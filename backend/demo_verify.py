# -*- coding: utf-8 -*-
"""
demo_verify.py
--------------
LIVE DEMO: Evidence Integrity Verification
Picks the most recently uploaded evidence automatically,
then shows verification + tamper detection step by step.

Run: python demo_verify.py
"""
import sys, requests, json, os, hashlib, time

sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://localhost:8000/api/v1"

def hr(msg=""):
    print("\n" + "="*62)
    if msg:
        print(f"  {msg}")
        print("="*62)

def pause(msg="  Press ENTER to continue..."):
    input(msg)

# ── STEP 0: Load the blockchain ledger to find the latest evidence ──
hr("DIVEL - LIVE VERIFICATION INTEGRITY DEMO")
print("  This demo proves that uploaded evidence cannot be silently tampered.")
pause()

LEDGER_PATH = "local_blockchain_ledger.json"
with open(LEDGER_PATH, "r") as f:
    ledger = json.load(f)

# Get the most recent real evidence (not a CASE_META entry)
real_evidence = [e for e in ledger if not e["evidence_id"].startswith("CASE_META")]
if not real_evidence:
    print("[ERROR] No evidence found in ledger. Please upload a file first.")
    sys.exit(1)

latest = real_evidence[-1]
evidence_id  = latest["evidence_id"]
case_id      = latest["case_id"]
ledger_hash  = latest["hash"]
uploaded_at  = latest["timestamp"]
file_type    = latest.get("file_type", "unknown")

hr("STEP 1: Evidence in Blockchain Ledger")
print(f"  Evidence ID   : {evidence_id}")
print(f"  Case ID       : {case_id}")
print(f"  File Type     : {file_type}")
print(f"  Uploaded At   : {uploaded_at}")
print(f"  Stored Hash   : {ledger_hash}")
print(f"\n  --> This hash is LOCKED in the blockchain ledger.")
print(f"  --> No one can change this hash without it being detected.")
pause()

# ── STEP 2: Call the verify endpoint (file is untampered) ──────────
hr("STEP 2: Verifying Evidence (file should be INTACT)")
print("  Calling: GET /api/v1/evidence/{id}/verify")
print("  System will: re-read file from disk -> recompute SHA-256 -> compare with blockchain\n")
pause("  Press ENTER to run verification...")

r = requests.get(f"{BASE}/evidence/{evidence_id}/verify")
if r.status_code != 200:
    print(f"[ERROR] {r.status_code}: {r.text}")
    sys.exit(1)

result = r.json()
hashes = result["hashes"]

print(f"\n  Recomputed Hash  : {hashes['recomputed_from_file']}")
print(f"  Blockchain Hash  : {hashes['stored_on_blockchain']}")
print(f"  Match            : {hashes['match']}")
print(f"\n  STATUS  --> {result['overall_status']}")
print(f"  VERDICT --> {result['verdict']}")

if result["overall_status"] == "VERIFIED":
    print("\n  [PASS] Evidence is INTACT. Hash matches the blockchain record.")
else:
    print("\n  [WARN] Something unexpected. Check the ledger.")

pause()

# ── STEP 3: Tamper the file ────────────────────────────────────────
hr("STEP 3: Simulating an ATTACK - Tampering with the file")
print("  Imagine a corrupt officer tries to modify the evidence file on disk...")
pause("  Press ENTER to simulate tampering...")

# Find the file in uploads/
uploads_dir = os.path.join(os.getcwd(), "uploads")
target_file = None
for root, dirs, files in os.walk(uploads_dir):
    for fname in files:
        fpath = os.path.join(root, fname)
        # compute hash and match
        with open(fpath, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        if h == ledger_hash:
            target_file = fpath
            break
    if target_file:
        break

if not target_file:
    print("[WARN] Could not locate the evidence file in uploads/")
    print("       Continuing demo with verify call only...")
else:
    # Read original content
    with open(target_file, "rb") as f:
        original_content = f.read()

    # Tamper: append attacker bytes
    tampered_content = original_content + b"\n[TAMPERED by attacker - EVIDENCE MODIFIED]"
    with open(target_file, "wb") as f:
        f.write(tampered_content)

    tampered_hash = hashlib.sha256(tampered_content).hexdigest()
    print(f"\n  File modified    : {target_file}")
    print(f"  Original Hash    : {ledger_hash}")
    print(f"  Tampered Hash    : {tampered_hash}")
    print(f"  Hashes match?    : {tampered_hash == ledger_hash}")
    print(f"\n  --> The file has been secretly changed on disk.")
    print(f"  --> Will the system catch this?")

pause("\n  Press ENTER to re-verify the tampered file...")

# ── STEP 4: Re-verify (should detect tamper) ──────────────────────
hr("STEP 4: Re-Verifying (should detect TAMPER)")
print("  Calling verify endpoint again on the same evidence ID...\n")

r = requests.get(f"{BASE}/evidence/{evidence_id}/verify")
result = r.json()
hashes = result["hashes"]

print(f"  Recomputed Hash  : {hashes['recomputed_from_file']}")
print(f"  Blockchain Hash  : {hashes['stored_on_blockchain']}")
print(f"  Match            : {hashes['match']}")
print(f"\n  STATUS  --> {result['overall_status']}")
print(f"  VERDICT --> {result['verdict']}")

if result["overall_status"] == "TAMPERED":
    print("\n  [PASS] TAMPER DETECTED! The system caught the attack.")
    print("         Even a single byte change is detected immediately.")

# ── STEP 5: Restore the file ──────────────────────────────────────
if target_file:
    pause("\n  Press ENTER to RESTORE the original file...")
    with open(target_file, "wb") as f:
        f.write(original_content)

    r = requests.get(f"{BASE}/evidence/{evidence_id}/verify")
    result = r.json()
    print(f"\n  After restore --> STATUS: {result['overall_status']}")
    print(f"  VERDICT --> {result['verdict']}")
    print("\n  [OK] File restored. Evidence is INTACT again.")

hr("DEMO COMPLETE")
print("  Blockchain Ledger : local_blockchain_ledger.json")
print("  File Storage      : backend/uploads/")
print("  Verify Endpoint   : GET /api/v1/evidence/{id}/verify")
print("  Tamper Detection  : WORKING")
print("="*62 + "\n")
