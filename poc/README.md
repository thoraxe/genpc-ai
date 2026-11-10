# NPC Knowledge Engine: PoC

A Python engine plus a bare test page. NPCs know what they saw or heard, gossip loses detail as it spreads, memories fade over in-game days, and loading a save rolls all of it back. The page uses the same HTTP API a game mod would.

## Setup
- **`.env` at the repo root** needs:
  - `ZAI_API_KEY`: a z.ai Coding Plan key.
  - `ELEVENLABS_API_KEY`: needs the `voices_read` and text-to-speech permissions.
- **Optional settings:**
  - `LLM_BASE_URL`, `LLM_MODEL` (default `glm-5.3-flash`) and `LLM_API_KEY_ENV`, to point at any OpenAI-compatible provider.
  - `TTS_ENABLED=0`, to turn voice off.

```
uv run python poc/scripts/smoke.py      # check both providers + timings
uv run pytest -q                        # offline tests (no network)
uv run uvicorn engine.api:app --app-dir poc --port 8000   # then open http://localhost:8000
uv run python poc/scripts/eval.py 10    # live eval against the real LLM (~1 min)
```

## Demo script (about 3 minutes)
1. **Reset the world to day 41.** Click Torvald and ask for the news: he has nothing. Click Sabine: the same.
2. **Clear the bandits at Embershard Mine, with Hrolf as the witness.** Talk to Hrolf: he has every detail (steel armor, dusk, the leader, the axe).
3. **Save** ("before gossip").
4. **+½ day.** Talk to Torvald: he brings up the mine himself and knows about the loot. The Inspector shows the axe and dusk details struck through as *lost in retelling*.
   - Tell him your name and something about yourself. The turn shows "will remember: …".
5. **+1 day twice (day 44).** Talk to Eirik in Whiterun and ask what was taken: "Couldn't tell you." He only has the two most important facts.
6. **Talk to Sabine in Solitude:** still nothing. Click **Show prompt** to see that the event isn't in her prompt at all.
7. **+7 days, then +30 days.** Watch Torvald's memories in the Inspector:
   - they turn yellow (gist) and the minor facts fade;
   - eventually they turn red (forgotten).
   - Talk to him: he remembers only the gist of you.
8. **Load "before gossip".** Torvald, Eirik and your conversation are all gone, as if it never happened.

## Layout
`engine/`:
- `models.py`
- `knowledge.py`: the deterministic rules.
- `store.py`: SQLite and save slots.
- `dialog.py`: prompt → LLM → validate → memory.
- `providers/`: `llm.py` and `tts.py`.
- `api.py`

`data/`:
- `world.json`: settlements, adjacency, NPCs and their voices.
- `events.json`: preset events.

`ui/index.html` · `tests/` · `scripts/`
