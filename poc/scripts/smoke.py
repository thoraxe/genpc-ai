"""M0 smoke test: one z.ai JSON-mode call and one ElevenLabs streamed TTS call, with timings.

Run: uv run python poc/scripts/smoke.py
Never prints API keys.
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")  # z.ai errors can be in Chinese; Windows console defaults to cp1252
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

ZAI_BASE = os.getenv(
    "ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4/"
)  # Coding Plan key; standard keys use /api/paas/v4/
ZAI_MODEL = os.getenv("ZAI_MODEL", "glm-5.3-flash")
EL_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")


def check_zai() -> bool:
    key = os.getenv("ZAI_API_KEY")
    if not key:
        print("[zai] ZAI_API_KEY missing")
        return False
    client = OpenAI(api_key=key, base_url=ZAI_BASE, timeout=30)
    prompt = (
        "You are Orgnar, a terse innkeeper. Reply with JSON only: "
        '{"npc_line": "<one sentence greeting>", "choices": ["<3 short player replies>"]}'
    )
    t0 = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=ZAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            reasoning_effort="low",  # GLM-5.3 thinking cannot be disabled; low keeps it ~2s
            max_tokens=200,
        )
    except Exception as e:  # report and continue to the TTS check
        print(f"[zai] FAILED ({type(e).__name__}): {str(e)[:300]}")
        return False
    dt = time.perf_counter() - t0
    content = resp.choices[0].message.content or ""
    try:
        data = json.loads(content)
        ok = isinstance(data.get("npc_line"), str) and isinstance(data.get("choices"), list)
    except json.JSONDecodeError:
        data, ok = content, False
    usage = getattr(resp, "usage", None)
    print(f"[zai] model={ZAI_MODEL} total={dt:.2f}s valid_json={ok} usage={usage and usage.model_dump()}")
    print(f"[zai] reply: {data}")
    return ok


def check_elevenlabs() -> bool:
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        print("[11labs] ELEVENLABS_API_KEY missing")
        return False
    h = {"xi-api-key": key}
    with httpx.Client(timeout=30) as c:
        # Listing voices needs the voices_read permission; a restricted key may only allow TTS.
        vid = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # premade "George"
        r = c.get("https://api.elevenlabs.io/v1/voices", headers=h)
        if r.status_code == 200:
            voices = r.json().get("voices", [])
            print(f"[11labs] {len(voices)} voices available, e.g.:")
            for v in voices[:8]:
                labels = v.get("labels") or {}
                print(
                    f"   {v['voice_id']}  {v['name']}  {labels.get('gender', '')} {labels.get('age', '')} {labels.get('accent', '')}"
                )
        else:
            print(f"[11labs] voices list unavailable ({r.status_code}); trying TTS with voice {vid}")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/stream?output_format=mp3_44100_128"
        body = {"text": "Word is someone cleared out the old mine. Was that you?", "model_id": EL_MODEL}
        out = ROOT / "poc" / "var" / "smoke.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        first = None
        n = 0
        with c.stream("POST", url, headers=h, json=body) as s:
            if s.status_code != 200:
                print(f"[11labs] tts FAILED {s.status_code}: {s.read()[:300]!r}")
                return False
            with open(out, "wb") as f:
                for chunk in s.iter_bytes():
                    if first is None:
                        first = time.perf_counter() - t0
                    n += len(chunk)
                    f.write(chunk)
        total = time.perf_counter() - t0
        print(f"[11labs] model={EL_MODEL} first_byte={first:.2f}s total={total:.2f}s bytes={n} -> {out}")
        return n > 0


if __name__ == "__main__":
    a = check_zai()
    b = check_elevenlabs()
    print(f"\nRESULT zai={'OK' if a else 'FAIL'} elevenlabs={'OK' if b else 'FAIL'}")
    sys.exit(0 if a and b else 1)
