"""Simple CLI to transcribe an audio file using OpenAI's API.

Usage:
  python transcribe-troy.py path/to/audio.mp3

Requirements:
  - Set OPENAI_API_KEY in your environment.
  - Install dependencies from requirements.txt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from openai import OpenAI


def main() -> int:
    if "OPENAI_API_KEY" not in os.environ:
        print("ERROR: Set OPENAI_API_KEY environment variable.", file=sys.stderr)
        return 1

    if len(sys.argv) < 2:
        print("Usage: python transcribe-troy.py <audio-file>", file=sys.stderr)
        return 2

    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print(f"ERROR: File not found: {audio_path}", file=sys.stderr)
        return 3

    client = OpenAI()
    with audio_path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
        )

    print(transcription.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
