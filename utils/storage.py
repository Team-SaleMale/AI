import mimetypes
import os
import uuid
from typing import BinaryIO

import boto3
from botocore.config import Config

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

if not all([S3_BUCKET_NAME, S3_REGION]):
    raise RuntimeError("S3_BUCKET_NAME 및 S3_REGION 환경 변수가 필요합니다.")

session_kwargs = {
    "region_name": S3_REGION,
}

if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    session_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    session_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

session = boto3.session.Session(**session_kwargs)
s3_client = session.client(
    "s3",
    config=Config(retries={"max_attempts": 3, "mode": "standard"}),
)


def _build_key(prefix: str, filename: str) -> str:
    ext = os.path.splitext(filename or "")[1] or ".bin"
    return f"{prefix.rstrip('/')}/{uuid.uuid4().hex}{ext}"


def _public_url(key: str) -> str:
    return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{key}"


def upload_fileobj(
    file_obj: BinaryIO,
    filename: str,
    prefix: str,
    content_type: str | None = None,
) -> str:
    key = _build_key(prefix, filename)
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type
    s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, key, ExtraArgs=extra_args)
    return _public_url(key)


def upload_local_file(path: str, prefix: str) -> str:
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    key = _build_key(prefix, os.path.basename(path))
    with open(path, "rb") as fp:
        s3_client.upload_fileobj(fp, S3_BUCKET_NAME, key, ExtraArgs={"ContentType": content_type})
    return _public_url(key)

