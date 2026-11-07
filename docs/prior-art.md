# Prior Art (verified 2026-11-07)

Method: Mantella and CHIM checked by reading source; SkyrimNet, Inworld, Convai and ACE from docs and press only. Nexus pages were unreachable (403).

## Verdict
- **Novel:** a deterministic witness → hop chain where detail drops at each hop (a). The academic precedent is Talk of the Town (Ryan et al., ~2015–16), which isn't LLM-based and isn't a modding backend.
- **Partial:**
  - (b) Decay with consolidation into a gist: SkyrimNet claims this, but it's closed source.
  - (d) Game-agnostic backend for modders: Mantella and CHIM have pluggable LLM/TTS but are tied to Bethesda games.
  - (e) Generated choice menus: no evidence anyone does this. Only Mantella was verified (free chat); CHIM and SkyrimNet are unconfirmed.
- **Already done:** (c) save awareness at the event level. CHIM prunes the event log on load (`processor/comm.php`), and its optional "Dragon Break" snapshots the abandoned timeline. CHIM's pruning of derived summaries is commented out as obsolete.

## Matrix
| | (a) lossy gossip | (b) time decay→gist | (c) save-aware | (d) agnostic backend | (e) choice menus |
|---|---|---|---|---|---|
| Mantella (AGPL-3.0) | Partial: one-hop LLM `ShareConversation` | Partial: re-summarizes by size | No: memory per character via `world_id`, no rollback | Partial: Skyrim/FO4 | No: free chat |
| CHIM (GPL-3.0) | Partial: witness filter + hold-wide LLM rumors | Partial: embeddings, diary | Yes: event-level prune on load | Partial: Skyrim, ~15 LLM / ~28 TTS backends | Unknown |
| SkyrimNet (closed) | Partial: LLM gossip | Yes (claimed) | Unknown | No | Unknown |
| Inworld / Convai / ACE | No | Partial | No | SDKs for studios, not modders | Unknown |
| Talk of the Town | Yes (non-LLM) | Yes | n/a | No | n/a |
| Generative Agents | Partial: emergent | Partial: reflections | n/a | n/a | n/a |

## Sources
- https://github.com/art-from-the-machine/Mantella · https://github.com/art-from-the-machine/Mantella-Spell
- https://github.com/Dwemer-Dynamics/HerikaServer
- https://github.com/MinLL/SkyrimNet-GamePlugin · https://goncalo22.github.io/SkyrimNet-GamePlugin/Features/overview
- https://docs.inworld.ai/guides/runtime-character · https://convai.com/blog/long-term-memeory
- https://www.nvidia.com/en-eu/geforce/news/nvidia-ace-autonomous-ai-companions-pubg-naraka-bladepoint/
- https://aitopics.org/doc/conferences:EA0682D9 (Talk of the Town) · https://mkremins.github.io/publications/Gossamer_CoG2023.pdf
