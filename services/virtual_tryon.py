import os
from typing import Tuple

from gradio_client import Client, file as gradio_file

from utils.storage import upload_local_file

HF_SPACE_ID = os.getenv("HF_SPACE_ID", "yisol/IDM-VTON")
HF_API_TOKEN = os.getenv("HF_API_TOKEN") or None

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        kwargs = {}
        if HF_API_TOKEN:
            kwargs["hf_token"] = HF_API_TOKEN
        _client = Client(HF_SPACE_ID, **kwargs)
    return _client


def run_virtual_tryon(
    background_url: str,
    garment_url: str,
    garment_desc: str,
    is_checked: bool = True,
    crop: bool = False,
    denoise_steps: int = 30,
    seed: int = 42,
) -> Tuple[str, str | None]:
    client = _get_client()
    result = client.predict(
        dict={"background": gradio_file(background_url), "layers": [], "composite": None},
        garm_img=gradio_file(garment_url),
        garment_des=garment_desc,
        is_checked=is_checked,
        is_checked_crop=crop,
        denoise_steps=denoise_steps,
        seed=seed,
        api_name="/tryon",
    )

    output_path, masked_path = result
    output_url = upload_local_file(output_path, "tryon/results")
    masked_url = upload_local_file(masked_path, "tryon/masked") if masked_path else None
    return output_url, masked_url

