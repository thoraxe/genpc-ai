# Monetization Feasibility (2026-11-07)

Labels: [V] read on the source page · [S] secondary or press source · [U] unverified or estimated.

## Verdict
Donations alone earn little, and the mod-site rules ban gating a mod behind payment. The realistic path is:
- the mod, the connectors and the engine (bring your own keys, or run locally) stay free and open source;
- money comes from a separate, optional **hosted service that isn't tied to any one game**;
- licensing to studios is possible upside, not something to plan around.

## What donations actually pay
- **Nexus Donation Points:** 1,000 DP = $1, from a monthly pool that Nexus sets at its own discretion. [V] help.nexusmods.com/article/112
  - The original worked example works out to about $2 per 1,000 unique downloads. [S]
- **SkyrimNet,** the closest competitor: about $850/month from 135 paying patrons. [V] graphtreon.com/creator/skyrimnet
- **Outliers:**
  - praydog (UEVR): about $0.5–2k/month.
  - Luke Ross (VR mods): about $10–20k/month gross, but only because access was gated.
- **Mantella, CHIM:** no public numbers.
- **Realistic range** for an ungated AI NPC mod: **about $0.5–2k/month.**

## Legal and ToS constraints
- **Nexus** bans:
  - charging for mods, files, updates or "modding-related services";
  - early access in exchange for donations;
  - linking to Patreon or Discord at all if anything is monetized;
  - stripped-down "lite" versions of a paid mod.

  **Open question:** does a paid external cloud service that a free mod connects to count as a "modding-related service"? Get a written answer from Nexus support before launch. [V] help.nexusmods.com/article/77
- **Bethesda:**
  - The Creation Kit licence allows non-commercial use only.
  - The only legal way to sell a mod is the Verified Creator program (Creations), and Creations bans generative-AI content. [S]
- **CD Projekt Red:**
  - The Fan Content Guidelines forbid monetizing its IP; you must ask in advance. [V] cdprojektred.com/fan-content
  - In January 2026 it issued a DMCA takedown against Luke Ross's Patreon-gated Cyberpunk VR mod. He argued it contained no CDPR assets, and the takedown happened anyway. [S]
  - **Treat Cyberpunk as free only.**
- **Voices:**
  - Nexus's November 2026 rules require AI disclosure, and cloned voices are removed on a credible complaint. [S]
  - SAG-AFTRA's 2025 agreement requires consent and real-time pay, which binds studios that license the engine. [S]
  - ElevenLabs bans cloning a voice without consent. [S]
  - **The paid service never hosts clones of game actors.**
- **Precedents for paid tools:**
  - The modding tools themselves are all free: Wabbajack (whose policy bans paywalls), ENB, MO2/Vortex and Community Shaders.
  - Paid tools that sell are game-agnostic utilities: VoiceAttack, Lossless Scaling. [U prices]

## Business models
| Model | Precedent | Fit |
|---|---|---|
| Free mod + paid hosted backend at about $8–15/month with usage caps, sold on our own site | None found: Mantella, CHIM and SkyrimNet all have users bring their own keys | **Best**: an open niche |
| Patreon, no gating | SkyrimNet, about $850/month | Goodwill and marketing |
| Middleware licence for indie/AA studios (AGPL + commercial, sold in asset stores) | Inworld pivoted to a general consumer runtime in Aug 2025; Charisma looks to have moved to film | Upside only: studio demand looks weak |
| Standalone Steam "tool" | VoiceAttack | Possible way to sell the hosted client |

**Cost per user per hour [U]:** about 120 turns per hour, 3k prompt tokens and 100 output tokens per turn, about 200 characters of speech per turn.
- Cheap LLM: about $0.03–0.15.
- Inworld-class TTS: about $0.12–0.24. ElevenLabs-class: about $1–3.
- **Budget stack: about $0.20–0.50 per hour,** so a $10/month plan needs a cap of roughly 10–20 hours.

## Decide early
1. **Licence:** AGPL-3.0 plus a commercial licence, with a contributor agreement (CLA) from the first commit. Relicensing later is painful.
2. **Split:** the paid parts (hosted service, content-pack tooling) contain no game assets, game names or branding. Only the free connectors touch any one game.
3. **Cyberpunk:** free only, or ask CDPR legal first.
4. **Voices:** licensed or synthetic only in anything paid. Any local cloning stays on the user's own machine.
5. **Nexus:** written clarification on linking to a paid external service.
6. **Cost controls:** prompt caching, the pre-generation option, and local TTS for the bulk of lines.

## Gaps
No current Nexus DP rate per download · no revenue numbers for Mantella or CHIM · no published Verified Creator revenue share · no official Convai or NVIDIA ACE pricing.

## Sources
https://help.nexusmods.com/article/112-donation-points-faq · https://help.nexusmods.com/article/77-donation-options-guidelines · https://graphtreon.com/creator/skyrimnet · https://graphtreon.com/creator/praydog · https://mixed-news.com/en/this-vr-modder-makes-10000-a-month/ · https://en.uesp.net/wiki/Tes5Mod:EULA · https://www.pcgamesn.com/skyrim/mods-creations-ai · https://cdprojektred.com/fan-content/ · https://www.gamesradar.com/games/cyberpunk/cyberpunk-2077-vr-mod-hit-with-dmca-takedown-cd-projekt-red-is-happy-for-it-to-return-if-its-made-free-but-its-creator-wont-budge-im-sorry-but-i-dont-believe-you-are-within-your-rights · https://wiki.wabbajack.org/policies_and_license/Wabbajack%20Monetization%20Policy.html · https://www.gaming.net/nexus-mods-expands-ai-rules-but-rejects-an-outright-ban/ · https://decrypt.co/329479/video-game-performers-ai-consent-rules · https://elevenlabs.io/use-policy · https://inworld.ai/pricing · https://www.globenewswire.com/news-release/2025/08/13/3132320/0/en/inworld-runtime-the-first-ai-runtime-for-consumer-applications.html
