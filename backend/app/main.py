from fastapi import FastAPI, UploadFile, File, HTTPException
from openai import OpenAI
import os
from typing import Any

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
async def transcribe(file: UploadFile = File(...)) -> dict[str, Any]:
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
