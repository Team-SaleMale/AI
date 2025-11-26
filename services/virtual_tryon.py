import base64
import json
import os
from typing import Tuple

import requests

HF_SPACE_ID = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON")
HF_API_TOKEN = os.getenv("HF_API_TOKEN") or None
HF_REQUEST_TIMEOUT = int(os.getenv("HF_REQUEST_TIMEOUT", "600"))


def _build_space_url() -> str:
    # allow overriding with full url
    if HF_SPACE_ID.startswith("http"):
        return HF_SPACE_ID.rstrip("/")
    return f"https://{HF_SPACE_ID.replace('/', '-').lower()}.hf.space"


HF_BASE_URL = _build_space_url()


def _to_data_url(content: bytes, content_type: str | None) -> str | None:
    if not content:
        return None
    mime = content_type or "image/png"
    encoded = base64.b64encode(content).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _extract_media(entries, index: int) -> str | None:
    if not entries or len(entries) <= index:
        return None
    entry = entries[index]
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("url") or entry.get("data")
    if isinstance(entry, list) and entry:
        return _extract_media(entry, 0)
    return None


def run_virtual_tryon(
    background_bytes: bytes,
    background_content_type: str | None,
    background_filename: str | None,
    garment_bytes: bytes,
    garment_content_type: str | None,
    garment_filename: str | None,
    garment_desc: str,
    is_checked: bool = True,
    crop: bool = False,
    denoise_steps: int = 30,
    seed: int = 42,
) -> Tuple[str, str | None]:
    headers = {}
    if HF_API_TOKEN:
        headers["Authorization"] = f"Bearer {HF_API_TOKEN}"

    editor_payload = {
        "background": _to_data_url(background_bytes, background_content_type),
        "layers": [],
        "composite": None,
    }

    files = {
        "dict": (None, json.dumps(editor_payload), "application/json"),
        "garm_img": (
            garment_filename or "garment.png",
            garment_bytes,
            garment_content_type or "application/octet-stream",
        ),
    }

    data = {
        "garment_des": garment_desc,
        "is_checked": str(is_checked).lower(),
        "is_checked_crop": str(crop).lower(),
        "denoise_steps": str(denoise_steps),
        "seed": str(seed),
    }

    response = requests.post(
        f"{HF_BASE_URL}/tryon",
        data=data,
        files=files,
        headers=headers,
        timeout=HF_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    outputs = payload.get("data", [])
    result_media = _extract_media(outputs, 0)
    masked_media = _extract_media(outputs, 1)

    if not result_media:
        raise RuntimeError("Hugging Face 응답에서 결과 이미지를 찾을 수 없습니다.")

    return result_media, masked_media

