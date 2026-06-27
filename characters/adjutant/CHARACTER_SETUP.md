# Creating the "Adjutant" Character in Runway

Everything needed to stand up the conversational avatar. **Character creation is a
portal step** (no API for it) — follow the walkthrough, then we wire up the integration
with the resulting **Avatar ID**.

## Files in this folder
| File | Use in the portal |
|---|---|
| `adjutant_source.png` | The character image (upload this) — 1920×1088, front-facing, centered |
| `adjutant_source_upscaled.png` | 4K (3840×2176) Magnific-upscaled version for a crisper source |
| `adjutant_online_test.mp4` | Motion preview (penetrating stare, fluttering lashes, slow nod) |
| `system_prompt.txt` | Paste into the **Instructions / personality** field |
| `knowledge_base.txt` | Upload as a **Knowledge base** (.txt) — who she is, the Commander, the swarm |
| `knowledge_base_agentic_disciplines.txt` | Upload as a **Knowledge base** (.txt) — the SwarmForge Agentic Disciplines she enforces |
| `persona.md` | The persona rationale (background, not uploaded) |
| `exploration/` | Generation history — source icon, first test, image variants & finalists |

## Portal walkthrough
1. Sign in at **dev.runwayml.com** → open the **Characters** tab.
2. Click **Create a Character**.
3. **Upload image:** `adjutant_source.png`.
4. **Voice:** pick a preset that fits Adjutant, or design/clone one (see below). Preview it.
5. **Instructions (personality):** paste the contents of `system_prompt.txt`.
6. **Knowledge base (optional):** upload `knowledge_base.txt` and `knowledge_base_agentic_disciplines.txt`.
7. **Starting script (optional):** paste the opening line below.
8. Click **Create Character** → copy the **Avatar ID** (UUID). Save it; we'll need it.

## Voice spec
Target: **calm, measured, synthetic-feminine, mid-low register, confident** — a composed
mission-control operator with a faint digital texture, not warm-and-fuzzy.
- **Preset route:** choose the calm/composed female preset closest to that (e.g. a
  "Clara"/"Victoria"-type voice) and preview against the start line.
- **Custom route (recommended for personality):** design a voice from this prompt —
  > "A calm, composed female AI voice. Measured and precise, mid-to-low register, quietly
  > confident, with a faint synthetic/processed texture and a subtle dry edge. Unhurried,
  > never bubbly."
  Or clone from a 10–30s clean audio sample if you have a reference.

## Starting script (opening line)
> "General. Adjutant online. The fleet is standing by — what's our objective?"

## After creation — integration
Once you paste the Avatar ID here, the session flow is:
- Create a real-time session (model `gwm1_avatars`) → receive WebRTC credentials
  (retrievable **once**; recreate the session if the connection fails).
- Session states: `NOT_READY → READY → RUNNING → COMPLETED`; **max 5 minutes** per session.
- `personality` and `startScript` can be **overridden per session** for context injection
  without editing the base character.
- Embed via the Runway widget / React integration or LiveKit Agents.
- Pricing: `gwm1_avatars` ≈ 2 credits upfront + 2 credits / 6 seconds.

## Notes
- The persona rationale lives in `persona.md`.
- Source URLs from generation expire in 24h, but `adjutant_source.png` is saved locally.
</content>
