import boto3
import json
import os
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import List, Dict, Any, Optional
from decimal import Decimal
from urllib.parse import urlparse

# ── SERIALIZATION HELPERS FOR DYNAMODB ─────────────────────────
def float_to_decimal(obj):
    if isinstance(obj, float):
        # Using string representation to avoid precision inaccuracies
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(x) for x in obj]
    return obj

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        f = float(obj)
        return int(f) if f.is_integer() else f
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(x) for x in obj]
    return obj


class DatabaseService:
    def __init__(self):
        self.dynamodb_client = None
        self.cases_table = None
        self.evidence_table = None
        self.local_db_path = "local_db.json"
        self._ensure_database_connection()

    def _ensure_database_connection(self):
        print("[DatabaseService] AWS_ACCESS_KEY_ID=", settings.AWS_ACCESS_KEY_ID[:6] + "******" if settings.AWS_ACCESS_KEY_ID else None)
        print("[DatabaseService] AWS_REGION=", settings.AWS_REGION)
        print("[DatabaseService] DYNAMODB_TABLE_CASES=", settings.DYNAMODB_TABLE_CASES)
        print("[DatabaseService] DYNAMODB_TABLE_EVIDENCE=", settings.DYNAMODB_TABLE_EVIDENCE)
        print("[DatabaseService] AWS_SESSION_TOKEN=", "present" if settings.AWS_SESSION_TOKEN else "none")

        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and settings.DYNAMODB_TABLE_CASES and settings.DYNAMODB_TABLE_EVIDENCE:
            try:
                dynamodb_kwargs = {
                    'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                    'region_name': settings.AWS_REGION
                }
                if settings.AWS_SESSION_TOKEN:
                    dynamodb_kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN

                dynamodb = boto3.resource('dynamodb', **dynamodb_kwargs)
                cases_table = dynamodb.Table(settings.DYNAMODB_TABLE_CASES)
                evidence_table = dynamodb.Table(settings.DYNAMODB_TABLE_EVIDENCE)
                cases_table.load()
                evidence_table.load()
                self.cases_table = cases_table
                self.evidence_table = evidence_table
                print(f"Connected to DynamoDB Tables: {settings.DYNAMODB_TABLE_CASES}, {settings.DYNAMODB_TABLE_EVIDENCE}")
                return
            except Exception as e:
                print(f"Failed to connect to DynamoDB: {e}. DynamoDB-only mode enabled; no local fallback.")
                self.cases_table = None
                self.evidence_table = None
                return

    def _use_local_mode(self):
        self.cases_table = None
        self.evidence_table = None
        print("DynamoDB unavailable; no local fallback is configured.")

    def _init_local_db(self):
        pass

    def _read_local_db(self) -> Dict[str, Any]:
        raise RuntimeError("Local DB fallback disabled; DynamoDB connection required.")

    def _write_local_db(self, data: Dict[str, Any]):
        raise RuntimeError("Local DB fallback disabled; DynamoDB connection required.")

    def _normalize_evidence_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not metadata:
            return None

        normalized = dict(metadata)
        blockchain = metadata.get("blockchain") if isinstance(metadata.get("blockchain"), dict) else {}

        normalized["hash"] = metadata.get("hash") or metadata.get("file_hash")
        normalized["transaction_hash"] = metadata.get("transaction_hash") or metadata.get("tx_hash")
        normalized["bucket"] = metadata.get("bucket") or blockchain.get("bucket")
        normalized["object_key"] = metadata.get("object_key") or metadata.get("key") or blockchain.get("object_key")

        if not normalized.get("bucket") and isinstance(metadata.get("url"), str):
            parsed = urlparse(metadata["url"])
            if parsed.netloc and ".s3." in parsed.netloc:
                normalized["bucket"] = parsed.netloc.split(".s3.", 1)[0]
                normalized["object_key"] = parsed.path.lstrip("/")

        if not normalized.get("object_key") and isinstance(metadata.get("local_path"), str):
            parsed = urlparse(metadata["local_path"])
            if parsed.netloc and ".s3." in parsed.netloc:
                normalized["bucket"] = parsed.netloc.split(".s3.", 1)[0]
                normalized["object_key"] = parsed.path.lstrip("/")

        normalized["blockchain_status"] = (
            metadata.get("blockchain_status")
            or blockchain.get("blockchain_status")
            or ("anchored" if normalized.get("transaction_hash") else "failed")
        )
        normalized["network"] = metadata.get("network") or blockchain.get("network")
        normalized["contract_address"] = metadata.get("contract_address") or blockchain.get("contract_address")
        normalized["timestamp"] = metadata.get("timestamp") or blockchain.get("timestamp")
        normalized["previous_hash"] = metadata.get("previous_hash") or blockchain.get("previous_hash")
        normalized["uploader_role"] = metadata.get("uploader_role") or blockchain.get("uploader_role")

        return normalized

    def _persist_normalized_evidence(self, metadata: Dict[str, Any]) -> None:
        if self.evidence_table:
            try:
                self.evidence_table.put_item(Item=float_to_decimal(metadata))
            except ClientError:
                pass

    # ─────────────────────────────────────────────
    # CASES
    # ─────────────────────────────────────────────

    def list_cases(self) -> List[Dict[str, Any]]:
        if self.cases_table:
            try:
                response = self.cases_table.scan()
                items = response.get('Items', [])
                return decimal_to_float(items)
            except ClientError as e:
                print(f"DynamoDB list_cases Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for list_cases.")

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        if self.cases_table:
            try:
                response = self.cases_table.get_item(Key={'id': case_id})
                item = response.get('Item')
                return decimal_to_float(item) if item else None
            except ClientError as e:
                print(f"DynamoDB get_case Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for get_case.")

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.cases_table:
            try:
                db_item = float_to_decimal(case_data)
                self.cases_table.put_item(Item=db_item)
                return case_data
            except ClientError as e:
                print(f"DynamoDB create_case Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for create_case.")

    # ─────────────────────────────────────────────
    # EVIDENCE METADATA
    # ─────────────────────────────────────────────

    def store_evidence_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store or update evidence metadata in DB."""
        normalized_metadata = self._normalize_evidence_metadata(metadata)
        if self.evidence_table:
            try:
                self._persist_normalized_evidence(normalized_metadata)
                return normalized_metadata
            except ClientError as e:
                print(f"DynamoDB store_evidence_metadata Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for store_evidence_metadata.")

        # Replace if exists
        for i, e in enumerate(evidence_list):
            if e.get("evidence_id") == normalized_metadata.get("evidence_id"):
                evidence_list[i] = normalized_metadata
                data["evidence"] = evidence_list
                self._write_local_db(data)
                return normalized_metadata

        evidence_list.append(normalized_metadata)
        data["evidence"] = evidence_list
        self._write_local_db(data)
        return normalized_metadata

    def get_evidence_metadata(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get evidence metadata by evidence_id."""
        if self.evidence_table:
            try:
                response = self.evidence_table.get_item(Key={'evidence_id': evidence_id})
                item = response.get('Item')
                if item:
                    normalized = self._normalize_evidence_metadata(decimal_to_float(item))
                    if normalized and (
                        normalized.get("hash") != item.get("hash")
                        or normalized.get("transaction_hash") != item.get("transaction_hash")
                        or normalized.get("bucket") != item.get("bucket")
                        or normalized.get("object_key") != item.get("object_key")
                    ):
                        self._persist_normalized_evidence(normalized)
                    return normalized
                return None
            except ClientError as e:
                print(f"DynamoDB get_evidence_metadata Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for get_evidence_metadata.")

    def list_case_evidence(self, case_id: str) -> List[Dict[str, Any]]:
        """List all evidence metadata for a case."""
        if self.evidence_table:
            try:
                from boto3.dynamodb.conditions import Attr
                response = self.evidence_table.scan(
                    FilterExpression=Attr('case_id').eq(case_id)
                )
                items = response.get('Items', [])
                return decimal_to_float(items)
            except ClientError as e:
                print(f"DynamoDB list_case_evidence Error: {e}. DynamoDB-only mode enabled.")
                self._use_local_mode()
                raise

        raise RuntimeError("DynamoDB connection unavailable for list_case_evidence.")

    def add_evidence_to_case(self, case_id: str, evidence_metadata: Dict[str, Any]):
        """Add evidence entry into the case's evidence array."""
        if not self.cases_table:
            raise RuntimeError("DynamoDB connection unavailable for add_evidence_to_case.")

        try:
            case = self.get_case(case_id)
            if case:
                if "evidence" not in case or not case["evidence"]:
                    case["evidence"] = []
                # avoid duplicates
                existing_ids = [e.get("evidence_id") for e in case["evidence"]]
                if evidence_metadata.get("evidence_id") not in existing_ids:
                    case["evidence"].append(evidence_metadata)
                    self.create_case(case)
            return
        except ClientError as e:
            print(f"DynamoDB add_evidence_to_case Error: {e}. DynamoDB-only mode enabled.")
            self._use_local_mode()
            raise

    def update_evidence_in_case(self, case_id: str, evidence_id: str, updated_metadata: Dict[str, Any]):
        """Update a specific evidence entry inside a case's evidence array."""
        if not self.cases_table:
            raise RuntimeError("DynamoDB connection unavailable for update_evidence_in_case.")

        try:
            case = self.get_case(case_id)
            if case and "evidence" in case:
                for i, e in enumerate(case["evidence"]):
                    if e.get("evidence_id") == evidence_id:
                        case["evidence"][i] = updated_metadata
                        break
                self.create_case(case)
            return
        except ClientError as e:
            print(f"DynamoDB update_evidence_in_case Error: {e}. DynamoDB-only mode enabled.")
            self._use_local_mode()
            raise

db = DatabaseService()
