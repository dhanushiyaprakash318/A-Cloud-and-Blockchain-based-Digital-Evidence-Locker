import io

from app.services.storage import StorageService


class FakeS3Client:
    def __init__(self):
        self.calls = []

    def get_object(self, Bucket, Key):
        self.calls.append((Bucket, Key))
        return {"Body": io.BytesIO(b"aws-data")}


def test_get_file_bytes_uses_bucket_and_object_key_from_metadata():
    storage = StorageService()
    fake_s3 = FakeS3Client()
    storage.s3_client = fake_s3
    storage.bucket_name = "divel-evidence-vault"

    payload = {"bucket": "divel-evidence-vault", "object_key": "case-123/evidence.pdf"}
    data = storage.get_file_bytes(payload)

    assert data == b"aws-data"
    assert fake_s3.calls == [("divel-evidence-vault", "case-123/evidence.pdf")]
