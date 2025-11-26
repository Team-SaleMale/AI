import os
import uuid
from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.config import Config

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("S3_REGION") or os.getenv("AWS_S3_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

if not all([S3_BUCKET_NAME, S3_REGION]):
    raise RuntimeError("S3_BUCKET_NAME 및 S3_REGION 환경 변수가 필요합니다.")

_session_kwargs = {"region_name": S3_REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    _session_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    _session_kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

_session = boto3.session.Session(**_session_kwargs)
_s3_client = _session.client(
    "s3",
    config=Config(retries={"max_attempts": 3, "mode": "standard"}),
)


def upload_bytes(
    data: bytes,
    prefix: str,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """
    바이트 데이터를 S3에 업로드하고 공개 URL을 반환.
    """
    ext = ""
    if filename and "." in filename:
        ext = os.path.splitext(filename)[1]
    key = f"{prefix.rstrip('/')}/{uuid.uuid4().hex}{ext or '.png'}"

    extra_args: dict[str, str] = {}
    if content_type:
        extra_args["ContentType"] = content_type

    _s3_client.upload_fileobj(BytesIO(data), S3_BUCKET_NAME, key, ExtraArgs=extra_args)
    return f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{key}"

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}