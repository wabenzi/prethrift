import os
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from openai import OpenAI
from pydantic import BaseModel

from . import openai_extractor

app = FastAPI()
client: OpenAI | None = None


def get_client() -> OpenAI:
    global client
    if client is None:
        if "OPENAI_API_KEY" not in os.environ:
            raise RuntimeError("OPENAI_API_KEY not set")
        client = OpenAI()
    return client


@app.get("/")
def read_root():
    return {"message": "Prethrift API"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = None) -> dict[str, Any]:  # type: ignore[assignment]
    if file is None:  # FastAPI will inject UploadFile for 'file' form field
        raise HTTPException(status_code=400, detail="Missing file upload field 'file'")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")
    try:
        contents = await file.read()
        # OpenAI client expects a file-like object; use bytes via in-memory buffer
        import io

        buffer = io.BytesIO(contents)
        buffer.name = file.filename  # type: ignore[attr-defined]
        result = get_client().audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=buffer,
        )
        text = getattr(result, "text", None) or getattr(result, "data", {}).get("text")  # defensive
        return {"filename": file.filename, "text": text}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


class PreferenceExtractRequest(BaseModel):
    conversation: str
    model: str | None = None


@app.post("/preferences/extract")
def preferences_extract(req: PreferenceExtractRequest) -> dict[str, Any]:
    """Extract structured garment preferences from a conversation transcript.

    Body:
      conversation: Raw conversation text (required)
      model: Optional OpenAI model override (default gpt-4o-mini)
    """
    if not req.conversation.strip():
        raise HTTPException(status_code=400, detail="conversation must not be empty")
    try:
        result = openai_extractor.extract_preferences(
            conversation=req.conversation, model=req.model or "gpt-4o-mini"
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
