import base64
import mimetypes
import os
import tempfile
from typing import Tuple

from gradio_client import Client, file as gradio_file

HF_SPACE_ID = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON")
HF_API_TOKEN = os.getenv("HF_API_TOKEN") or None
HF_REQUEST_TIMEOUT = int(os.getenv("HF_REQUEST_TIMEOUT", "600"))

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        kwargs = {}
        if HF_API_TOKEN:
            kwargs["hf_token"] = HF_API_TOKEN
        _client = Client(HF_SPACE_ID, **kwargs)
    return _client


def _write_temp_file(data: bytes, filename: str | None) -> str:
    suffix = ""
    if filename and "." in filename:
        suffix = os.path.splitext(filename)[1]
    fd, path = tempfile.mkstemp(suffix=suffix or ".png")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _to_data_url_from_path(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


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
    client = _get_client()

    bg_path = _write_temp_file(background_bytes, background_filename)
    garment_path = _write_temp_file(garment_bytes, garment_filename)

    try:
        result = client.predict(
            dict={"background": gradio_file(bg_path), "layers": [], "composite": None},
            garm_img=gradio_file(garment_path),
            garment_des=garment_desc,
            is_checked=is_checked,
            is_checked_crop=crop,
            denoise_steps=denoise_steps,
            seed=seed,
            api_name="/tryon",
        )
    finally:
        try:
            os.remove(bg_path)
        except OSError:
            pass
        try:
            os.remove(garment_path)
        except OSError:
            pass

    output_path, masked_path = result
    result_url = _to_data_url_from_path(output_path)
    masked_url = _to_data_url_from_path(masked_path) if masked_path else None
    return result_url, masked_url

