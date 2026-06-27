import boto3
import json
import os
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import List, Dict, Any, Optional
from decimal import Decimal

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
                print(f"Failed to connect to DynamoDB: {e}. Falling back to local_db.json")

        self._use_local_mode()

    def _use_local_mode(self):
        self.cases_table = None
        self.evidence_table = None
        print("Running in Local Mode (Using local_db.json)")
        self._init_local_db()

    def _init_local_db(self):
        if not os.path.exists(self.local_db_path):
            with open(self.local_db_path, 'w') as f:
                json.dump({"cases": [], "evidence": []}, f)

    def _read_local_db(self) -> Dict[str, Any]:
        with open(self.local_db_path, 'r') as f:
            return json.load(f)

    def _write_local_db(self, data: Dict[str, Any]):
        with open(self.local_db_path, 'w') as f:
            json.dump(data, f, indent=4)

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
                print(f"DynamoDB list_cases Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        return data.get("cases", [])

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        if self.cases_table:
            try:
                response = self.cases_table.get_item(Key={'id': case_id})
                item = response.get('Item')
                return decimal_to_float(item) if item else None
            except ClientError as e:
                print(f"DynamoDB get_case Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        for case in data.get("cases", []):
            if case.get("id") == case_id:
                return case
        return None

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.cases_table:
            try:
                db_item = float_to_decimal(case_data)
                self.cases_table.put_item(Item=db_item)
                return case_data
            except ClientError as e:
                print(f"DynamoDB create_case Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        # Replace if exists, else append
        cases = data.get("cases", [])
        for i, c in enumerate(cases):
            if c.get("id") == case_data.get("id"):
                cases[i] = case_data
                data["cases"] = cases
                self._write_local_db(data)
                return case_data
        data["cases"].append(case_data)
        self._write_local_db(data)
        return case_data

    # ─────────────────────────────────────────────
    # EVIDENCE METADATA
    # ─────────────────────────────────────────────

    def store_evidence_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store or update evidence metadata in DB."""
        if self.evidence_table:
            try:
                db_item = float_to_decimal(metadata)
                self.evidence_table.put_item(Item=db_item)
                return metadata
            except ClientError as e:
                print(f"DynamoDB store_evidence_metadata Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        evidence_list = data.get("evidence", [])

        # Replace if exists
        for i, e in enumerate(evidence_list):
            if e.get("evidence_id") == metadata.get("evidence_id"):
                evidence_list[i] = metadata
                data["evidence"] = evidence_list
                self._write_local_db(data)
                return metadata

        evidence_list.append(metadata)
        data["evidence"] = evidence_list
        self._write_local_db(data)
        return metadata

    def get_evidence_metadata(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get evidence metadata by evidence_id."""
        if self.evidence_table:
            try:
                response = self.evidence_table.get_item(Key={'evidence_id': evidence_id})
                item = response.get('Item')
                return decimal_to_float(item) if item else None
            except ClientError as e:
                print(f"DynamoDB get_evidence_metadata Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        for e in data.get("evidence", []):
            if e.get("evidence_id") == evidence_id:
                return e
        return None

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
                print(f"DynamoDB list_case_evidence Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        return [e for e in data.get("evidence", []) if e.get("case_id") == case_id]

    def add_evidence_to_case(self, case_id: str, evidence_metadata: Dict[str, Any]):
        """Add evidence entry into the case's evidence array."""
        if self.cases_table:
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
                print(f"DynamoDB add_evidence_to_case Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        for case in data.get("cases", []):
            if case.get("id") == case_id:
                if "evidence" not in case:
                    case["evidence"] = []
                # avoid duplicates
                existing_ids = [e.get("evidence_id") for e in case["evidence"]]
                if evidence_metadata.get("evidence_id") not in existing_ids:
                    case["evidence"].append(evidence_metadata)
                break
        self._write_local_db(data)

    def update_evidence_in_case(self, case_id: str, evidence_id: str, updated_metadata: Dict[str, Any]):
        """Update a specific evidence entry inside a case's evidence array."""
        if self.cases_table:
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
                print(f"DynamoDB update_evidence_in_case Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        for case in data.get("cases", []):
            if case.get("id") == case_id:
                for i, e in enumerate(case.get("evidence", [])):
                    if e.get("evidence_id") == evidence_id:
                        case["evidence"][i] = updated_metadata
                        break
                break
        self._write_local_db(data)

db = DatabaseService()
