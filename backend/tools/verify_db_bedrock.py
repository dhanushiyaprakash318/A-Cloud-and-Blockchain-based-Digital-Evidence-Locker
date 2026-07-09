# tools/verify_db_bedrock.py
import os
import sys
import asyncio

# Ensure the backend package can be imported when running from the tools directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services import database, bedrock_service

def verify():
    print("DynamoDB tables object present?:", bool(database.db.cases_table and database.db.evidence_table))
    print("Bedrock client present?:", bool(bedrock_service.bedrock.client))

    # If bedrock client exists, try a small converse call to Nova (timeout may apply)
    if bedrock_service.bedrock.client:
        try:
            resp = bedrock_service.bedrock.converse(
                model_id="amazon.nova-lite-v1:0",
                input_text="show me the summary for evidence_id 5d648ec0-4594-4298-b153-2a04bc77d2a1"
            )
            print("Bedrock response text (truncated):", (resp.get("text") or "")[:300])
        except Exception as e:
            print("Bedrock converse failed:", e)

if __name__ == "__main__":
    verify()