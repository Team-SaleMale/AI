import mimetypes
import os
import tempfile
from typing import Tuple

from gradio_client import Client, file as gradio_file

from utils.storage import upload_bytes
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
        # submit으로 job을 만들고, HF_REQUEST_TIMEOUT(초) 만큼만 대기
        job = client.submit(
            dict={"background": gradio_file(bg_path), "layers": [], "composite": None},
            garm_img=gradio_file(garment_path),
            garment_des=garment_desc,
            is_checked=is_checked,
            is_checked_crop=crop,
            denoise_steps=denoise_steps,
            seed=seed,
            api_name="/tryon",
        )
        result = job.result(timeout=HF_REQUEST_TIMEOUT)
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

    # 결과 이미지를 읽어서 S3에 업로드
    with open(output_path, "rb") as f:
        output_bytes = f.read()
    output_mime = mimetypes.guess_type(output_path)[0] or "image/png"
    result_url = upload_bytes(
        output_bytes,
        prefix="tryon/results",
        filename=os.path.basename(output_path),
        content_type=output_mime,
    )

    masked_url: str | None = None
    if masked_path:
        with open(masked_path, "rb") as f:
            masked_bytes = f.read()
        masked_mime = mimetypes.guess_type(masked_path)[0] or "image/png"
        masked_url = upload_bytes(
            masked_bytes,
            prefix="tryon/masked",
            filename=os.path.basename(masked_path),
            content_type=masked_mime,
        )

    return result_url, masked_url


