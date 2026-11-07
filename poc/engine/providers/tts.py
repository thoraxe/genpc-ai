"""TTS provider interface + ElevenLabs streaming implementation with an on-disk cache.

The engine plays nothing itself in the PoC: the browser streams /api/audio/{turn_id}.
(For a game client without lip-sync, the engine could play the same stream locally.)
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterator, Protocol

import httpx


class TTSProvider(Protocol):
    name: str
    media_type: str

    def stream(self, text: str, voice_id: str) -> Iterator[bytes]: ...


class ElevenLabsTTS:
    media_type = "audio/mpeg"

    def __init__(self, api_key: str, model: str = "eleven_flash_v2_5",
                 output_format: str = "mp3_44100_128", cache_dir: str | Path | None = None):
        self.name = f"elevenlabs:{model}"
        self.api_key, self.model, self.output_format = api_key, model, output_format
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, voice_id: str) -> Path | None:
        if not self.cache_dir:
            return None
        h = hashlib.sha256(f"{self.model}|{self.output_format}|{voice_id}|{text}".encode()).hexdigest()[:32]
        return self.cache_dir / f"{h}.mp3"

    def stream(self, text: str, voice_id: str) -> Iterator[bytes]:
        path = self._cache_path(text, voice_id)
        if path and path.exists():
            yield path.read_bytes()
            return
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format={self.output_format}"
        tmp = path.with_suffix(".part") if path else None
        with httpx.stream("POST", url, headers={"xi-api-key": self.api_key},
                          json={"text": text, "model_id": self.model}, timeout=30) as r:
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs {r.status_code}: {r.read()[:200]!r}")
            f = open(tmp, "wb") if tmp else None
            try:
                for chunk in r.iter_bytes():
                    if f:
                        f.write(chunk)
                    yield chunk
            finally:
                if f:
                    f.close()
        if tmp:
            tmp.replace(path)  # only complete files enter the cache


def from_env(cache_dir: str | Path | None = None) -> ElevenLabsTTS | None:
    if os.getenv("TTS_ENABLED", "1") in ("0", "false", "no"):
        return None
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return None
    return ElevenLabsTTS(key, model=os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5"), cache_dir=cache_dir)
