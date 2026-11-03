from google.cloud import storage
from datetime import timedelta
from typing import Optional


class GCSStorageService:

    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(
        self,
        file_path: str,
        destination_blob_name: str,
        content_type: Optional[str] = None
    ) -> dict:

        blob = self.bucket.blob(destination_blob_name)

        blob.upload_from_filename(
            file_path,
            content_type=content_type
        )

        return {
            "bucket": self.bucket.name,
            "objectKey": destination_blob_name,
            "fileName": destination_blob_name.split("/")[-1]
        }
    
    def upload_bytes(
        self,
        file_content: bytes,
        destination_blob_name: str,
        content_type: str = "application/octet-stream"
    ) -> dict:

        blob = self.bucket.blob(destination_blob_name)

        blob.upload_from_string(
            file_content,
            content_type=content_type
        )

        return {
            "bucket": self.bucket.name,
            "objectKey": destination_blob_name,
            "fileName": destination_blob_name.split("/")[-1]
        }

    def generate_signed_url(
        self,
        object_key: str,
        expiration_minutes: int = 60
    ) -> str:

        blob = self.bucket.blob(object_key)

        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET"
        )