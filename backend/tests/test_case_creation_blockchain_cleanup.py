import asyncio
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import cases, evidence
from app.models.case import CaseCreate


class FakeDB:
    def __init__(self):
        self.saved = None

    def create_case(self, case_data):
        self.saved = case_data
        return case_data


class DummyBlockchain:
    def __init__(self):
        self.rpc_url = "http://disabled"

    def calculate_hash(self, payload):
        return "deadbeef"

    def store_hash_on_chain(self, **kwargs):
        raise AssertionError("Local blockchain transaction should not be called during case creation")


def test_create_case_skips_local_blockchain_transaction(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(cases, "db", fake_db)
    monkeypatch.setattr(cases, "blockchain", DummyBlockchain())

    case_payload = CaseCreate(
        district="North",
        unit="Cyber",
        lawSections=["Section 1"],
        dateOfOffence="2025-01-01",
        dateOfReport="2025-01-02",
        sceneOfCrime="HQ",
        latitude=12.34,
        longitude=56.78,
        accused=[],
    )

    response = cases.create_case(case_payload)

    assert response["case_created"] is True
    assert fake_db.saved is not None
    assert response["case"]["hash"] == "deadbeef"
    assert response["blockchain_status"] in {"disabled", "lambda-managed", "pending"}


def test_upload_evidence_records_failed_lambda_metadata(monkeypatch):
    class FakeEvidenceDB:
        def __init__(self):
            self.saved = []
            self.case_updates = []

        def store_evidence_metadata(self, metadata):
            self.saved.append(metadata)
            return metadata

        def add_evidence_to_case(self, case_id, metadata):
            self.case_updates.append((case_id, metadata))

        def update_evidence_in_case(self, case_id, evidence_id, metadata):
            self.case_updates.append((case_id, evidence_id, metadata))

    fake_db = FakeEvidenceDB()
    monkeypatch.setattr(evidence, "db", fake_db)
    monkeypatch.setattr(evidence.storage, "upload_file", lambda file_obj, s3_object_key, file_type: "/tmp/test-file")
    monkeypatch.setattr(evidence.storage, "bucket_name", "test-bucket")
    monkeypatch.setattr(evidence.ai_service, "generate_summary", lambda path: {"summary": "", "graph": {"nodes": [], "links": []}})

    def raise_lambda_error(*args, **kwargs):
        raise RuntimeError("lambda exploded")

    monkeypatch.setattr(evidence.requests, "post", raise_lambda_error)

    upload_file = UploadFile(filename="test.txt", file=io.BytesIO(b"abc"))
    current_user = SimpleNamespace(username="alice", role="analyst")

    response = asyncio.run(evidence.upload_evidence(upload_file, "case-123", current_user))

    assert response["filename"] == "test.txt"
    assert any(item.get("blockchain_status") == "failed" and item.get("error") == "lambda exploded" for item in fake_db.saved)
