import os
import tempfile
from typing import Any

import torch
from fastapi import APIRouter, UploadFile, HTTPException

router = APIRouter(prefix="/speech")

try:  # pragma: no cover - optional dependency
    import whisperx  # type: ignore
except Exception as e:  # pragma: no cover
    whisperx = None  # type: ignore


_STT_MODEL: Any | None = None
_STT_DEVICE = "cuda" if torch.cuda.is_available() else (
    "mps" if torch.backends.mps.is_available() else "cpu"
)


def _get_whisperx_model() -> Any:
    global _STT_MODEL
    if whisperx is None:
        raise RuntimeError("whisperx is not installed on the model server")

    if _STT_MODEL is None:
        _STT_MODEL = whisperx.load_model("medium", _STT_DEVICE)
    return _STT_MODEL


@router.post("/whisperx")
async def transcribe_whisperx(file: UploadFile) -> dict[str, str]:
    if whisperx is None:
        raise HTTPException(
            status_code=500,
            detail="whisperx is not installed on the model server",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio file")

    suffix = os.path.splitext(file.filename or "audio")[1] or ".wav"
    tmp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        audio = whisperx.load_audio(tmp_path)
        model = _get_whisperx_model()
        result = model.transcribe(audio)

        text = ""
        if isinstance(result, dict):
            text = result.get("text") or ""
        return {"text": text}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"WhisperX STT failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
