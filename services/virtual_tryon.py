import mimetypes
import os
import tempfile
from typing import Tuple, List, Optional

from gradio_client import Client, file as gradio_file

from utils.storage import upload_bytes

HF_SPACE_ID = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON")
HF_REQUEST_TIMEOUT = int(os.getenv("HF_REQUEST_TIMEOUT", "600"))

# 여러 토큰을 콤마로 구분해 받을 수 있도록 지원 (HF_API_TOKENS 우선)
_hf_tokens_raw = os.getenv("HF_API_TOKENS") or os.getenv("HF_API_TOKEN") or ""
HF_API_TOKENS: List[str] = [t.strip() for t in _hf_tokens_raw.split(",") if t.strip()]


def _make_client(token: Optional[str]) -> Client:
    kwargs = {}
    if token:
        kwargs["hf_token"] = token
    return Client(HF_SPACE_ID, **kwargs)


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
    if not HF_API_TOKENS:
        # 토큰이 없으면 익명 호출 시도 (공개 Space인 경우만 동작)
        tokens_to_try: List[Optional[str]] = [None]
    else:
        tokens_to_try = [t for t in HF_API_TOKENS]

    bg_path = _write_temp_file(background_bytes, background_filename)
    garment_path = _write_temp_file(garment_bytes, garment_filename)

    last_error: Optional[Exception] = None

    try:
        for token in tokens_to_try:
            client = _make_client(token)
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
                break  # 성공하면 루프 종료
            except Exception as exc:
                last_error = exc
                msg = str(exc)
                # ZeroGPU 쿼터 초과 같은 경우에만 다음 토큰으로 넘어감
                if "ZeroGPU" in msg or "quota" in msg:
                    continue
                # 그 외 에러는 바로 중단
                raise
        else:
            # 모든 토큰이 실패한 경우
            raise RuntimeError(f"Hugging Face 호출 실패 (모든 토큰 소진): {last_error}")
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


