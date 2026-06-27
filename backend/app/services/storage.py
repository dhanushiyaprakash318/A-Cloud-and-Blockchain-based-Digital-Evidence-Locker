import boto3
import os
from typing import BinaryIO
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME

        if settings.AWS_ACCESS_KEY_ID:
            try:
                s3_kwargs = {
                    'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                    'region_name': settings.AWS_REGION
                }
                if settings.AWS_SESSION_TOKEN:
                    s3_kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN

                self.s3_client = boto3.client('s3', **s3_kwargs)
            except Exception as e:
                print(f"S3 client init failed: {e}. Using local storage.")
                self.s3_client = None

    def upload_file(self, file_obj: BinaryIO, filename: str, content_type: str) -> str:
        if self.s3_client and self.bucket_name:
            try:
                file_obj.seek(0)
                extra_args = {'ContentType': content_type}
                if settings.S3_ENCRYPTION:
                    extra_args['ServerSideEncryption'] = settings.S3_ENCRYPTION
                    if settings.S3_ENCRYPTION == 'aws:kms' and settings.S3_KMS_KEY_ID:
                        extra_args['SSEKMSKeyId'] = settings.S3_KMS_KEY_ID
                
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    filename,
                    ExtraArgs=extra_args
                )
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
            except Exception as e:
                print(f"S3 upload failed: {e}. Falling back to local storage.")

        # ── LOCAL STORAGE FALLBACK ──────────────────────────────────────
        local_path = os.path.join("uploads", filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        file_obj.seek(0)   # Reset position before reading
        with open(local_path, "wb") as f:
            f.write(file_obj.read())
        print(f"[LocalStorage] File saved to: {local_path}")
        return local_path  # Return the local path as the "url"

    def get_file_bytes(self, file_path: str) -> bytes:
        """
        Read file bytes from storage (local or S3).
        """
        # If it's an S3 URL or external URL, attempt to download it using the S3 client
        if file_path.startswith("http") or "amazonaws.com" in file_path:
            if self.s3_client and self.bucket_name:
                try:
                    if "amazonaws.com/" in file_path:
                        key = file_path.split("amazonaws.com/", 1)[1]
                    elif self.bucket_name in file_path:
                        key = file_path.split(self.bucket_name + "/", 1)[1]
                    else:
                        from urllib.parse import urlparse
                        parsed = urlparse(file_path)
                        key = parsed.path.lstrip('/')

                    print(f"[StorageService] Fetching file from S3: Key={key}")
                    response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                    return response['Body'].read()
                except Exception as e:
                    print(f"[StorageService] Failed to fetch file from S3: {e}")
                    # Fall through to HTTP fetch if URL is accessible directly
            else:
                print(f"[StorageService] S3 client not configured, attempting HTTP download: {file_path}")

            try:
                from urllib.request import urlopen
                print(f"[StorageService] Downloading remote file via HTTP: {file_path}")
                with urlopen(file_path) as response:
                    return response.read()
            except Exception as e:
                print(f"[StorageService] HTTP download failed: {e}")
                return None

        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()

        print(f"[StorageService] File not found locally: {file_path}")
        return None

storage = StorageService()
