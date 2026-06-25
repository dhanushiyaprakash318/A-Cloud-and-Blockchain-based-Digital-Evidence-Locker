import boto3
import os
from typing import BinaryIO
from app.core.config import settings

class StorageService:
    def __init__(self):
        # We initialize the client but check env vars before using
        self.s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
        
        if settings.AWS_ACCESS_KEY_ID:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )

    def upload_file(self, file_obj: BinaryIO, filename: str, content_type: str) -> str:
        if self.s3_client:
            try:
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket_name,
                    filename,
                    ExtraArgs={'ContentType': content_type}
                )
                return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
            except Exception as e:
                print(f"Error uploading to S3: {e}")
                # Fallback to local? For now, re-raise or return None
                raise e
        else:
            # Local Storage Mock
            local_path = f"uploads/{filename}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(file_obj.read())
            return local_path

    def get_file(self, filename: str):
        if self.s3_client:
            # returns a presigned url or the object
            pass 
        else:
            pass

storage = StorageService()
