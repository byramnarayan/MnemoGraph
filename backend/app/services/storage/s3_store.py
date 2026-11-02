from io import BytesIO
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.services.s3_service import _get_s3_client
from app.services.storage.object_store import BaseObjectStore


class S3ObjectStore(BaseObjectStore):
    """Stores exported notebook code and raw documents into S3/Neon object storage."""

    def __init__(self, bucket_name: str | None = None):
        self.bucket = bucket_name or settings.storage_bucket or settings.s3_bucket_name

    async def put_object(self, key: str, data: bytes, content_type: str = "text/plain") -> str:
        def _upload():
            s3 = _get_s3_client()
            s3.upload_fileobj(
                BytesIO(data),
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            return key

        return await run_in_threadpool(_upload)

    async def get_object(self, key: str) -> bytes:
        def _download():
            s3 = _get_s3_client()
            buf = BytesIO()
            s3.download_fileobj(self.bucket, key, buf)
            buf.seek(0)
            return buf.read()

        return await run_in_threadpool(_download)

    async def delete_object(self, key: str) -> None:
        def _del():
            s3 = _get_s3_client()
            s3.delete_object(Bucket=self.bucket, Key=key)

        await run_in_threadpool(_del)

    async def delete_prefix(self, prefix: str) -> int:
        def _del_prefix():
            s3 = _get_s3_client()
            paginator = s3.get_paginator("list_objects_v2")
            deleted_count = 0
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                objs = page.get("Contents", [])
                if objs:
                    delete_keys = [{"Key": obj["Key"]} for obj in objs]
                    s3.delete_objects(Bucket=self.bucket, Delete={"Objects": delete_keys})
                    deleted_count += len(delete_keys)
            return deleted_count

        return await run_in_threadpool(_del_prefix)


S3Store = S3ObjectStore

