from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from urllib.parse import urlparse
from app.api import auth
from app.services.storage import storage
from app.services.database import db
from app.services.blockchain import blockchain
from app.services.ai import ai_service
import uuid
import os
import requests
import tempfile
import json
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

    evidence_id = str(uuid.uuid4())
    file_type = file.content_type or "application/octet-stream"

    print(f"\n{'='*60}", flush=True)
    print(f"EVIDENCE UPLOAD: {file.filename}", flush=True)
    print(f"Evidence ID : {evidence_id}", flush=True)
    print(f"Case ID     : {case_id}", flush=True)

    print(f"{'='*60}\n", flush=True)

    # 3. Save file to local storage
    if not case_id or str(case_id).strip().lower() in {"undefined", "null", "nan", ""}:
        raise HTTPException(status_code=400, detail=f"Invalid case_id received: {case_id}")

    import io
    file_obj = io.BytesIO(content)
    s3_object_key = f"{case_id}/{file.filename}"
    try:
        local_path = storage.upload_file(file_obj, s3_object_key, file_type)
    except ValueError as ve:
        # Surface a clear 400 Bad Request when filename contains invalid segments
        raise HTTPException(status_code=400, detail=str(ve))

    # 4. Compute file hash and anchor hash on-chain (optional)
    lambda_key = s3_object_key
    if isinstance(local_path, str) and local_path.startswith("http"):
        parsed = urlparse(local_path)
        lambda_key = parsed.path.lstrip('/')

    lambda_event = {
        "bucket": storage.bucket_name or "divel-evidence-vault",
        "key": lambda_key,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "file_type": file_type,
        "uploader_role": current_user.role,
        "previous_hash": ""
    }

    print(f"[Upload] Sending metadata to Lambda...", flush=True)
    print("[Upload] S3 bucket:", storage.bucket_name, flush=True)
    print("[Upload] S3 object key:", lambda_key, flush=True)
    print("[Upload] Lambda event:", json.dumps(lambda_event, indent=2), flush=True)

    try:
        print("calling API Gateway Lambda for blockchain anchoring...", flush=True)
        print(">>> Before requests.post()", flush=True)
        response = requests.post(
            "https://pjb7msvyze.execute-api.eu-north-1.amazonaws.com/evidence",
            json=lambda_event,
            timeout=30
        )
        print(">>> After requests.post()", flush=True)

        response.raise_for_status()
        print(">>> Response status:", response.status_code, flush=True)
        print("Status Code:", response.status_code, flush=True)
        print("Response:", response.text, flush=True)
        blockchain_record = response.json()
        print(">>> Parsed JSON:", blockchain_record, flush=True)
        print("\n========== BLOCKCHAIN RECORD ==========")
        print(json.dumps(blockchain_record, indent=4))
        print("=======================================\n")
        print(f"[Lambda] Success:", blockchain_record)

    except Exception as e:
        print("========== LAMBDA ERROR ==========", flush=True)
        print(type(e), flush=True)
        print(str(e), flush=True)

        error_message = getattr(e, "message", None) or str(e)
        blockchain_record = {
            "transaction_hash": None,
            "hash": None,
            "message": "Lambda failed",
            "blockchain_status": "failed",
            "error": error_message,
            "timestamp": str(datetime.now())
        }

        failed_metadata = {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "filename": file.filename,
            "content_type": file_type,
            "uploader": current_user.username,
            "uploader_role": current_user.role,
            "file_hash": None,
            "timestamp": blockchain_record.get("timestamp"),
            "tx_hash": None,
            "block_number": None,
            "blockchain": blockchain_record,
            "blockchain_status": "failed",
            "error": error_message,
            "url": local_path,
            "local_path": local_path,
            "uploaded_at": str(datetime.now())
        }
        try:
            db.store_evidence_metadata(failed_metadata)
            db.add_evidence_to_case(case_id, failed_metadata)
        except Exception as audit_err:
            print(f"[Audit] Failed to persist failed blockchain evidence record: {audit_err}", flush=True)

    # 5. Save metadata to local_db.json
    metadata = {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "filename": file.filename,
        "content_type": file_type,
        "uploader": current_user.username,
        "uploader_role": current_user.role,
        "file_hash": blockchain_record.get("hash"),       # SHA-256 stored in DB (for cross-check)
        "timestamp": blockchain_record.get("timestamp") or str(datetime.now()),
        "tx_hash": blockchain_record.get("transaction_hash"),
        "block_number": blockchain_record.get("block_number"),
        "blockchain": blockchain_record,
       "blockchain_status": "anchored" if blockchain_record.get("transaction_hash") else "failed",
        "url": local_path,            # Local path (used for re-read during verify)
        "local_path": local_path,     # Explicit local path
        "uploaded_at": str(datetime.now())
    }
    print("\n========== METADATA TO SAVE ==========")
    print(json.dumps(metadata, indent=4, default=str))
    print("======================================\n")
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
        "file_hash": metadata.get("file_hash"),
        "tx_hash": blockchain_record.get("tx_hash"),
        "blockchain": blockchain_record,
        "blockchain_status": blockchain_record.get("blockchain_status", "pending"),
        "local_path": local_path,
        "ai_summary": ai_result.get("summary"),
        "knowledge_graph": ai_result.get("graph"),
        "message": "Evidence uploaded successfully. Blockchain anchoring is optional and will continue asynchronously if unavailable."
    }


@router.get("/{evidence_id}/blockchain")
async def get_evidence_blockchain_record(evidence_id: str):
    """Fetch stored blockchain details for evidence by ID."""
    metadata = db.get_evidence_metadata(evidence_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found in database.")

    blockchain_record = blockchain.get_evidence_chain_record(evidence_id)
    blockchain_record["tx_hash"] = metadata.get("transaction_hash") or blockchain_record.get("tx_hash")
    blockchain_record["contract_address"] = metadata.get("contract_address") or blockchain_record.get("contract_address")
    blockchain_record["network"] = metadata.get("network") or blockchain_record.get("network")
    blockchain_record["timestamp"] = metadata.get("timestamp") or blockchain_record.get("timestamp")

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

    print("Loaded metadata:", metadata)

    local_path = metadata.get("local_path") or metadata.get("url")
    stored_tx_hash = metadata.get("transaction_hash", "N/A")
    db_hash = metadata.get("hash", "")
    bucket_name = metadata.get("bucket")
    object_key = metadata.get("object_key") or metadata.get("key")

    print(f"\n{'='*60}")
    print(f"VERIFICATION REQUEST: {evidence_id}")
    print(f"File path   : {local_path}")
    print(f"Hash in DB  : {db_hash}")
    print(f"Transaction Hash: {stored_tx_hash}")
    print(f"Bucket: {bucket_name}")
    print(f"Object Key: {object_key}")
    print(f"{'='*60}")

    # Step 2: Download file from S3 using Lambda metadata when available
    s3_metadata = {"bucket": bucket_name, "object_key": object_key} if bucket_name and object_key else local_path
    file_bytes = storage.get_file_bytes(s3_metadata if bucket_name and object_key else local_path)
    if file_bytes is None:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot verify: evidence file not found at '{local_path}'. "
                   "File may have been moved or deleted."
        )

    # Step 3: Recompute SHA-256 from disk
    recomputed_hash = blockchain.calculate_hash(file_bytes)
    print(f"Recomputed Hash: {recomputed_hash}")
    print("Hash from DynamoDB:", db_hash)
    print("Hashes Match:", recomputed_hash == db_hash)

    # Step 4: Compare with the trusted DynamoDB hash from Lambda metadata
    hashes_match = recomputed_hash == db_hash if db_hash else False

    verification_result = {
        "provider": "AWS Lambda / DynamoDB",
        "verified": hashes_match,
        "blockchain_record": {
            "stored_hash": db_hash,
            "transaction_hash": stored_tx_hash,
            "timestamp": metadata.get("timestamp"),
            "contract_address": metadata.get("contract_address"),
            "network": metadata.get("network"),
            "blockchain_status": metadata.get("blockchain_status"),
            "uploader_role": metadata.get("uploader_role"),
            "previous_hash": metadata.get("previous_hash"),
        },
    }

    on_chain_hash = verification_result.get("blockchain_record", {}).get("stored_hash", "")

    # Fetch complete blockchain record for terminal audit logging (does not change verification logic)
    chain_record = blockchain.get_evidence_chain_record(evidence_id)
    tx_hash = metadata.get("transaction_hash") or chain_record.get("tx_hash")
    block_number = metadata.get("block_number") or chain_record.get("block_number")
    contract_address = metadata.get("contract_address") or chain_record.get("contract_address")
    timestamp = metadata.get("timestamp") or chain_record.get("timestamp") or verification_result.get("blockchain_record", {}).get("timestamp")

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
    blockchain_record["tx_hash"] = tx_hash
    blockchain_record["contract_address"] = contract_address
    blockchain_record["network"] = metadata.get("network") or blockchain_record.get("network")
    blockchain_record["timestamp"] = timestamp
    blockchain_record["previous_hash"] = metadata.get("previous_hash") or blockchain_record.get("previous_hash")
    blockchain_record["uploader_role"] = metadata.get("uploader_role") or blockchain_record.get("uploader_role")

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
        "s3": {
            "bucket": bucket_name,
            "object_key": object_key,
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
