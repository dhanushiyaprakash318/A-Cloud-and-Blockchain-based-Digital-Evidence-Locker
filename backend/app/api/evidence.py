from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from app.api import auth
from app.services.storage import storage
from app.services.database import db
from app.services.blockchain import blockchain
from app.services.ai import ai_service
import uuid
import os
import tempfile
from datetime import datetime

router = APIRouter()


@router.get("/{case_id}")
def get_case_evidence(case_id: str):
    """Get all evidence metadata for a specific case."""
    return db.list_case_evidence(case_id)


@router.post("/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    current_user: auth.User = Depends(auth.get_mock_polaris_user)
):
    """
    Upload evidence file:
      1. Read file bytes
      2. Compute SHA-256 hash
      3. Save file to local storage (uploads/)
      4. Store hash on-chain (Hardhat smart contract)
      5. Save metadata (including local_path + tx_hash) to local_db.json
      6. Run AI summary
    """
    # 1. Read file content
    content = await file.read()

    # 2. Compute SHA-256 hash
    file_hash = blockchain.calculate_hash(content)
    evidence_id = str(uuid.uuid4())
    file_type = file.content_type or "application/octet-stream"

    print(f"\n{'='*60}", flush=True)
    print(f"EVIDENCE UPLOAD: {file.filename}", flush=True)
    print(f"Evidence ID : {evidence_id}", flush=True)
    print(f"Case ID     : {case_id}", flush=True)
    print(f"SHA-256 Hash: {file_hash}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # 3. Save file to local storage
    import io
    file_obj = io.BytesIO(content)
    local_path = storage.upload_file(file_obj, f"{case_id}/{file.filename}", file_type)

    # 4. Anchor hash on-chain (Hardhat EvidenceRegistry contract)
    print(f"[Upload] evidence upload incoming for case: {case_id}, file: {file.filename}", flush=True)

    blockchain_record = blockchain.store_hash_on_chain(
        case_id=case_id,
        evidence_id=evidence_id,
        file_hash=file_hash,
        file_type=file_type,
        uploader_role=current_user.role,
        previous_hash=""
    )

    print(f"[Blockchain] TX Hash       : {blockchain_record.get('tx_hash')}", flush=True)
    print(f"[Blockchain] Stored Hash   : {blockchain_record.get('stored_hash')}", flush=True)

    # 5. Save metadata to local_db.json
    metadata = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "filename": file.filename,
        "content_type": file_type,
        "uploader": current_user.username,
        "uploader_role": current_user.role,
        "file_hash": file_hash,       # SHA-256 stored in DB (for cross-check)
        "tx_hash": blockchain_record.get("tx_hash"),
        "blockchain": blockchain_record,
        "url": local_path,            # Local path (used for re-read during verify)
        "local_path": local_path,     # Explicit local path
        "uploaded_at": str(datetime.now())
    }
    db.store_evidence_metadata(metadata)
    db.add_evidence_to_case(case_id, metadata)

    # 6. AI Summary (sync for MVP) — non-fatal
    ai_result = {"summary": "", "graph": {"nodes": [], "links": []}}
    try:
        temp_file_path = os.path.join(tempfile.gettempdir(), f"{evidence_id}_{file.filename}")
        with open(temp_file_path, "wb") as f:
            f.write(content)

        ai_result = ai_service.generate_summary(temp_file_path)

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    except Exception as ai_err:
        print(f"[AI] Non-fatal AI error: {ai_err}")

    metadata["ai_summary"] = ai_result.get("summary", "")
    metadata["knowledge_graph"] = ai_result.get("graph", {})

    db.store_evidence_metadata(metadata)
    db.update_evidence_in_case(case_id, evidence_id, metadata)

    return {
        "evidence_id": evidence_id,
        "filename": file.filename,
        "file_hash": file_hash,
        "tx_hash": blockchain_record.get("tx_hash"),
        "blockchain": blockchain_record,
        "local_path": local_path,
        "ai_summary": ai_result.get("summary"),
        "knowledge_graph": ai_result.get("graph"),
        "message": "Evidence uploaded and anchored to blockchain successfully."
    }


@router.get("/{evidence_id}/blockchain")
async def get_evidence_blockchain_record(evidence_id: str):
    """Fetch stored blockchain details for evidence by ID."""
    metadata = db.get_evidence_metadata(evidence_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found in database.")

    blockchain_record = blockchain.get_evidence_chain_record(evidence_id)
    blockchain_record["tx_hash"] = metadata.get("tx_hash") or blockchain_record.get("tx_hash")

    return {
        "evidence_id": evidence_id,
        "blockchain": blockchain_record
    }


@router.get("/{evidence_id}/verify")
async def verify_evidence(evidence_id: str):
    """
    Verify evidence integrity:
      1. Load metadata from local_db.json
      2. Re-read the evidence file from local storage
      3. Recompute SHA-256 hash from the file bytes
      4. Compare recomputed hash with the hash stored on the blockchain (smart contract)
      5. Return VERIFIED if they match, TAMPERED if they don't
    """
    # Step 1: Load metadata
    metadata = db.get_evidence_metadata(evidence_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found in database.")

    local_path = metadata.get("local_path") or metadata.get("url")
    stored_tx_hash = metadata.get("tx_hash", "N/A")
    db_hash = metadata.get("file_hash", "")

    print(f"\n{'='*60}")
    print(f"VERIFICATION REQUEST: {evidence_id}")
    print(f"File path   : {local_path}")
    print(f"Hash in DB  : {db_hash}")
    print(f"TX Hash     : {stored_tx_hash}")
    print(f"{'='*60}")

    # Step 2: Re-read file from disk
    file_bytes = storage.get_file_bytes(local_path)
    if file_bytes is None:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot verify: evidence file not found at '{local_path}'. "
                   "File may have been moved or deleted."
        )

    # Step 3: Recompute SHA-256 from disk
    recomputed_hash = blockchain.calculate_hash(file_bytes)
    print(f"Recomputed Hash: {recomputed_hash}")

    # Step 4: Compare with on-chain hash (smart contract)
    verification_result = blockchain.verify_integrity(evidence_id, recomputed_hash)

    # Determine final verdict
    on_chain_hash = verification_result.get("blockchain_record", {}).get("stored_hash", "")
    hashes_match = (recomputed_hash == on_chain_hash) if on_chain_hash else verification_result.get("verified", False)

    # Fetch complete blockchain record for terminal audit logging (does not change verification logic)
    chain_record = blockchain.get_evidence_chain_record(evidence_id)
    tx_hash = metadata.get("tx_hash") or chain_record.get("tx_hash")
    block_number = chain_record.get("block_number")
    contract_address = chain_record.get("contract_address")
    timestamp = chain_record.get("timestamp") or verification_result.get("blockchain_record", {}).get("timestamp")

    print(f"\n{'='*60}", flush=True)
    print("VERIFICATION AUDIT", flush=True)
    print(f"Evidence ID            : {evidence_id}", flush=True)
    print(f"Case ID                : {metadata.get('case_id')}", flush=True)
    print(f"Stored Blockchain Hash : {on_chain_hash}", flush=True)
    print(f"Current SHA-256 Hash   : {recomputed_hash}", flush=True)
    print(f"Transaction Hash       : {tx_hash}", flush=True)
    print(f"Block Number           : {block_number}", flush=True)
    print(f"Contract Address       : {contract_address}", flush=True)
    print(f"Timestamp              : {timestamp}", flush=True)
    print(f"Verification Result    : {'AUTHENTIC' if hashes_match else 'TAMPERED'}", flush=True)
    print(f"{'='*60}\n", flush=True)

    blockchain_record = verification_result.get("blockchain_record", {})

    return {
        "evidence_id": evidence_id,
        "filename": metadata.get("filename"),
        "case_id": metadata.get("case_id"),
        "overall_status": "VERIFIED" if hashes_match else "TAMPERED",
        "verdict": "✅ Evidence is INTACT — hash matches blockchain record." if hashes_match
                   else "🚨 TAMPER DETECTED — file has been modified after upload!",
        "hashes": {
            "recomputed_from_file": recomputed_hash,
            "stored_on_blockchain": on_chain_hash,
            "stored_in_db": db_hash,
            "match": hashes_match
        },
        "blockchain": {
            "tx_hash": stored_tx_hash,
            "provider": verification_result.get("provider", "Hardhat Local Node"),
            "timestamp": blockchain_record.get("timestamp", "N/A"),
            "uploader_role": blockchain_record.get("uploader_role", "N/A"),
            "contract_address": blockchain_record.get("contract_address"),
            "chain_id": blockchain_record.get("chain_id"),
            "block_number": blockchain_record.get("block_number"),
            "gas_used": blockchain_record.get("gas_used"),
            "network": blockchain_record.get("network"),
            "stored_hash": blockchain_record.get("stored_hash"),
            "previous_hash": blockchain_record.get("previous_hash"),
        }
    }
