import uuid
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool

from app.core.config import settings


def _get_s3_client():
    # Prioritize AWS_* object storage settings if provided, fallback to S3_*
    endpoint_url = settings.aws_endpoint_url_s3 or settings.s3_endpoint_url
    region_name = settings.aws_region or settings.s3_region

    access_key = None
    if settings.aws_access_key_id:
        access_key = settings.aws_access_key_id.get_secret_value()
    elif settings.s3_access_key_id:
        access_key = settings.s3_access_key_id.get_secret_value()

    secret_key = None
    if settings.aws_secret_access_key:
        secret_key = settings.aws_secret_access_key.get_secret_value()
    elif settings.s3_secret_access_key:
        secret_key = settings.s3_secret_access_key.get_secret_value()

    kwargs = {
        "region_name": region_name,
    }
    if access_key:
        kwargs["aws_access_key_id"] = access_key
    if secret_key:
        kwargs["aws_secret_access_key"] = secret_key
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    return boto3.client("s3", **kwargs)


def get_profile_image_url(filename: str | None) -> str:
    """Generate a valid, viewable image URL for a profile avatar."""
    if not filename:
        return "/static/profile_pics/default.jpg"

    s3 = _get_s3_client()
    try:
        # Generate presigned URL (valid for 7 days)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket_name, "Key": f"profile_pics/{filename}"},
            ExpiresIn=7 * 24 * 3600,
        )
    except Exception as e:
        print(f"[Presigned URL Error]: {e}")
        return "/static/profile_pics/default.jpg"


def process_profile_image(content: bytes) -> tuple[bytes, str]:
    """Process and optimize profile avatar: strip EXIF, crop to 400x400 square JPEG."""
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)
        img = ImageOps.fit(img, (400, 400), method=Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        filename = f"{uuid.uuid4().hex}.jpg"
        output = BytesIO()
        img.save(output, "JPEG", quality=85, optimize=True)
        output.seek(0)
        return output.read(), filename


def _upload_to_s3(file_bytes: bytes, key: str) -> None:
    s3 = _get_s3_client()
    s3.upload_fileobj(
        BytesIO(file_bytes),
        settings.s3_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )


def _delete_from_s3(key: str) -> None:
    s3 = _get_s3_client()
    try:
        s3.delete_object(Bucket=settings.s3_bucket_name, Key=key)
    except ClientError:
        pass


async def upload_profile_image(file_bytes: bytes, filename: str) -> None:
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_upload_to_s3, file_bytes, key)


async def delete_profile_image(filename: str | None) -> None:
    if not filename:
        return
    key = f"profile_pics/{filename}"
    await run_in_threadpool(_delete_from_s3, key)

