import boto3
import json
import os
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import List, Dict, Any, Optional

class DatabaseService:
    def __init__(self):
        self.dynamodb_client = None
        self.cases_table = None
        self.evidence_table = None
        self.local_db_path = "local_db.json"
        self._ensure_database_connection()

    def _ensure_database_connection(self):
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                dynamodb = boto3.resource(
                    'dynamodb',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
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

    def list_cases(self) -> List[Dict[str, Any]]:
        if self.cases_table:
            try:
                response = self.cases_table.scan()
                return response.get('Items', [])
            except ClientError as e:
                print(f"DynamoDB Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        return data.get("cases", [])

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        if self.cases_table:
            try:
                response = self.cases_table.get_item(Key={'id': case_id})
                return response.get('Item')
            except ClientError as e:
                print(f"DynamoDB Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        cases = data.get("cases", [])
        for case in cases:
            if case.get("id") == case_id:
                return case
        return None

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.cases_table:
            try:
                self.cases_table.put_item(Item=case_data)
                return case_data
            except ClientError as e:
                print(f"DynamoDB Error: {e}. Falling back to local_db.json")
                self._use_local_mode()

        data = self._read_local_db()
        data["cases"].append(case_data)
        self._write_local_db(data)
        return case_data

db = DatabaseService()
