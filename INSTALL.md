# Install the engine

The engine is a small program that runs on your PC while you play. Game mods talk to it at `http://localhost:8000`. It knows nothing about any game until a mod sends it a world.

These steps are for Windows. They also work on macOS and Linux, with that system's own terminal.

## What you need

- An API key for an LLM. Any service that speaks the OpenAI API works. The default is z.ai.
- Optional: an ElevenLabs API key, if you want NPC voices. Without it, NPCs only show text.

You do **not** need to install Python yourself. uv installs the right version (3.12 or newer) the first time you run the engine.

## Steps

1. **Install uv.** Open PowerShell and run:
   ```
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Close PowerShell and open it again, so it finds `uv`.

2. **Get the engine.** Either install [Git](https://git-scm.com/download/win) and run:
   ```
   git clone https://github.com/thoraxe/genpc-ai
   cd genpc-ai
   ```
   or download the zip from https://github.com/thoraxe/genpc-ai (green **Code** button, **Download ZIP**), extract it, and `cd` into the folder.

3. **Add your keys.** In the `genpc-ai` folder, make a file named `.env` with these lines:
   ```
   ZAI_API_KEY=your-llm-key
   ELEVENLABS_API_KEY=your-elevenlabs-key
   ```
   Leave out the ElevenLabs line if you do not want voices. Keep this file private: it holds your keys.

   To use another LLM service, also set `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY_ENV` (the name of the line that holds your key). See [`poc/README.md`](poc/README.md).

4. **Start the engine.** In the `genpc-ai` folder, run:
   ```
   uv run uvicorn engine.api:app --app-dir poc --port 8000
   ```
   The first start takes a minute while uv downloads Python and the libraries. It is ready when it shows `Uvicorn running on http://127.0.0.1:8000`.

5. **Check it.** Open http://localhost:8000 in a browser. You see the engine's test page.

## While you play

- Start the engine **before** you start the game, and leave its window open.
- To stop the engine, click its window and press **Ctrl+C**.
- The engine only accepts connections from your own PC. Other computers cannot reach it.
- What the NPCs know is kept in the `poc/var/` folder, one file for each game world. To start every world again from nothing, stop the engine and empty that folder.

## Update

If you used Git, run `git pull` in the `genpc-ai` folder. If you used the zip, download it again and copy your `.env` file into the new folder.

## Game mods

Each mod has its own install guide:

- Cyberpunk 2077: [`mods/cyberpunk/INSTALL.md`](mods/cyberpunk/INSTALL.md)
