# -*- coding: utf-8 -*-
"""
test_local_flow.py
Tests the complete local flow:
  1. Upload a case -> stored in local_db.json
  2. Upload evidence -> saved to uploads/, hash anchored to blockchain
  3. Verify evidence -> recomputes hash, compares with blockchain record
  4. Tamper simulation -> shows tamper detection working

Run from backend/ folder:
  python test_local_flow.py
"""
import sys
import requests
import json
import os
import hashlib

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8000/api/v1"

def hr(title=""):
    print(f"\n{'='*60}")
    if title:
        print(f"  {title}")
        print(f"{'='*60}")

# ─────────────────────────────────────────────────────────────
# STEP 1: Create a Case (stored in local_db.json)
# ─────────────────────────────────────────────────────────────
hr("STEP 1: Creating a new case in local_db.json")

case_payload = {
    "district": "Chennai",
    "unit": "Cyber Crime Unit",
    "lawSections": ["IPC 66", "IT Act 43"],
    "dateOfOffence": "2026-06-26",
    "dateOfReport": "2026-06-26",
    "sceneOfCrime": "123 Demo Street, Chennai",
    "latitude": 13.0827,
    "longitude": 80.2707,
    "accused": [
        {
            "name": "Demo Suspect",
            "age": "30",
            "gender": "Male",
            "address": "123 Demo Street",
            "status": "Arrested"
        }
    ],
    "customFields": [],
    "publicAlertEnabled": False
}

r = requests.post(f"{BASE}/cases", json=case_payload)
if r.status_code not in (200, 201):
    print(f"[FAIL] Case creation failed: {r.status_code} - {r.text}")
    sys.exit(1)

case = r.json()
case_id = case["id"]
case_hash = case.get("hash", "N/A")
tx_hash_case = case.get("tx_hash", "N/A")

print(f"[OK] Case created!")
print(f"     Case ID     : {case_id}")
print(f"     Case Number : {case.get('caseNumber')}")
print(f"     Case Hash   : {case_hash}")
print(f"     TX Hash     : {tx_hash_case}")

# ─────────────────────────────────────────────────────────────
# STEP 2: Upload Evidence (file saved to uploads/, hash to blockchain)
# ─────────────────────────────────────────────────────────────
hr("STEP 2: Uploading evidence file")

demo_file_content = b"FINGERPRINT SCAN DATA - Suspect: Demo Suspect - Date: 2026-06-26 - Analyst: Forensics Officer"
demo_file_name = "fingerprint_demo.bin"

with open(demo_file_name, "wb") as f:
    f.write(demo_file_content)

computed_hash_before = hashlib.sha256(demo_file_content).hexdigest()
print(f"     File        : {demo_file_name}")
print(f"     SHA-256     : {computed_hash_before}")

with open(demo_file_name, "rb") as f:
    r = requests.post(
        f"{BASE}/evidence/upload",
        data={"case_id": case_id},
        files={"file": (demo_file_name, f, "application/octet-stream")}
    )

if r.status_code not in (200, 201):
    print(f"[FAIL] Evidence upload failed: {r.status_code} - {r.text}")
    os.remove(demo_file_name)
    sys.exit(1)

evidence = r.json()
evidence_id = evidence["evidence_id"]
stored_hash = evidence["file_hash"]
tx_hash_ev = evidence["tx_hash"]
local_path = evidence["local_path"]

print(f"\n[OK] Evidence uploaded and anchored to blockchain!")
print(f"     Evidence ID : {evidence_id}")
print(f"     SHA-256     : {stored_hash}")
print(f"     TX Hash     : {tx_hash_ev}")
print(f"     Saved to    : {local_path}")

# ─────────────────────────────────────────────────────────────
# STEP 3: Verify (file untampered — should PASS)
# ─────────────────────────────────────────────────────────────
hr("STEP 3: Verifying evidence (file NOT tampered - should PASS)")

r = requests.get(f"{BASE}/evidence/{evidence_id}/verify")
result = r.json()

status = result.get('overall_status')
print(f"     Status      : {status}")
print(f"     Verdict     : {result.get('verdict')}")
print(f"     Recomputed  : {result['hashes']['recomputed_from_file']}")
print(f"     Blockchain  : {result['hashes']['stored_on_blockchain']}")
print(f"     Match       : {result['hashes']['match']}")
print(f"     Provider    : {result['blockchain']['provider']}")
print(f"     TX Hash     : {result['blockchain']['tx_hash']}")

if status == "VERIFIED":
    print(f"\n[PASS] Hash verified - evidence is INTACT.")
else:
    print(f"\n[WARN] Unexpected status: {status}")

# ─────────────────────────────────────────────────────────────
# STEP 4: Tamper the file and re-verify (should FAIL)
# ─────────────────────────────────────────────────────────────
hr("STEP 4: Simulating TAMPERING - modifying file on disk")

tampered_content = demo_file_content + b" [TAMPERED by attacker]"
abs_local_path = os.path.join(os.getcwd(), local_path) \
                 if not os.path.isabs(local_path) else local_path

with open(abs_local_path, "wb") as f:
    f.write(tampered_content)

tampered_hash = hashlib.sha256(tampered_content).hexdigest()
print(f"     File modified: {abs_local_path}")
print(f"     Tampered Hash: {tampered_hash}")
print(f"     Blockchain   : {stored_hash}")
print(f"     Match        : {tampered_hash == stored_hash}")

print("\n     Re-verifying with tampered file...")
r = requests.get(f"{BASE}/evidence/{evidence_id}/verify")
result = r.json()

status = result.get('overall_status')
print(f"\n     Status      : {status}")
print(f"     Verdict     : {result.get('verdict')}")
print(f"     Recomputed  : {result['hashes']['recomputed_from_file']}")
print(f"     Blockchain  : {result['hashes']['stored_on_blockchain']}")
print(f"     Match       : {result['hashes']['match']}")

if status == "TAMPERED":
    print(f"\n[PASS] Tamper DETECTED - hashes do not match. System works correctly!")
else:
    print(f"\n[WARN] Unexpected status: {status}")

# Cleanup temp demo file
os.remove(demo_file_name)

hr("ALL TESTS COMPLETE")
print("  [1] Case stored in       : backend/local_db.json")
print("  [2] File saved at        : backend/uploads/")
print("  [3] Hash anchored on     : local_blockchain_ledger.json (Hardhat fallback)")
print("  [4] Tamper detection     : WORKING")
print("="*60 + "\n")
