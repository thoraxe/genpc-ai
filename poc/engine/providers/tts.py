"""TTS provider interface + ElevenLabs streaming implementation.

The engine plays nothing itself in the PoC: the browser streams /api/audio/{turn_id}.
(For a game client without lip-sync, the engine could play the same stream locally.)
No cache: every NPC line is freshly generated, so repeats are rare.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Protocol

import httpx


class TTSProvider(Protocol):
    name: str
    media_type: str

    def stream(self, text: str, voice_id: str) -> Iterator[bytes]: ...


class ElevenLabsTTS:
    media_type = "audio/mpeg"

    def __init__(self, api_key: str, model: str = "eleven_flash_v2_5", output_format: str = "mp3_44100_128"):
        self.name = f"elevenlabs:{model}"
        self.api_key, self.model, self.output_format = api_key, model, output_format

    def stream(self, text: str, voice_id: str) -> Iterator[bytes]:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format={self.output_format}"
        with httpx.stream(
            "POST", url, headers={"xi-api-key": self.api_key}, json={"text": text, "model_id": self.model}, timeout=30
        ) as r:
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs {r.status_code}: {r.read()[:200]!r}")
            yield from r.iter_bytes()


def from_env() -> ElevenLabsTTS | None:
    if os.getenv("TTS_ENABLED", "1") in ("0", "false", "no"):
        return None
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return None
    return ElevenLabsTTS(key, model=os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5"))
