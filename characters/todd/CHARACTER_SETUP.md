# Creating the "Todd" Character in Runway

A conversational avatar of Todd Sorrel (Co-Founder & CEO, 6lock). **Character creation is
a portal step** (no API) — follow the walkthrough, then we wire up the integration with
the resulting **Avatar ID**.

## Files in this folder
| File | Use in the portal |
|---|---|
| `todd_source.jpeg` | The character image (upload this) — 800×800, front-facing, centered |
| `todd_test.mp4` | Motion preview (warm smile + welcoming nod) |
| `system_prompt.txt` | Paste into the **Instructions / personality** field |
| `knowledge_base.txt` | Upload as a **Knowledge base** (.txt) — who he is + how 6lock works |
| `persona.md` | The persona rationale (background, not uploaded) |
| `exploration/voice/todd_voice_sample.wav` | Clean 2:11 clip of Todd — **clone his voice from this** (.mp3 also provided) |
| `exploration/` | Scratch space (no look-variants generated — real likeness preserved) |

## Portal walkthrough
1. Sign in at **dev.runwayml.com** → open the **Characters** tab.
2. Click **Create a Character**.
3. **Upload image:** `todd_source.jpeg`.
4. **Voice:** pick a preset that fits Todd, or design/clone one (see below). Preview it.
5. **Instructions (personality):** paste the contents of `system_prompt.txt`.
6. **Knowledge base (optional):** upload `knowledge_base.txt`.
7. **Starting script (optional):** paste the opening line below.
8. Click **Create Character** → copy the **Avatar ID** (UUID). Save it; we'll need it.

## Voice spec
Target: **warm, fatherly, matter-of-fact, jubilant** — a relatively deep male voice with a
slight baritone, relaxed and unhurried, with light good-natured humor.
- **Preset route:** choose a warm, mid-deep male preset and preview against the start line.
- **Clone route (recommended — best likeness):** clone Todd's actual voice from
  `exploration/voice/todd_voice_sample.wav` (2:11 of clean solo Todd, cut from the
  "Billion-Dollar Blind Spot" podcast, 4:53–7:04). Upload it to Runway's Character voice
  ("clone from an audio sample") or to an ElevenLabs Instant Voice Clone.
- **Design route (fallback):** design a voice from this prompt —
  > "A warm, upbeat American male voice. Relatively deep with a slight baritone. Friendly
  > and fatherly, matter-of-fact and reassuring, relaxed and unhurried, with a touch of
  > light humor. Confident but never salesy."

## Starting script (opening line)
> "Hey, great to see you — I'm Todd, one of the founders of 6lock. Ask me anything; let's
> talk about taking the fraud and friction out of moving money in private markets."

## After creation — integration
- Create a real-time session (model `gwm1_avatars`) → WebRTC credentials (retrievable
  **once**; recreate the session if the connection fails).
- Session states: `NOT_READY → READY → RUNNING → COMPLETED`; **max 5 minutes** per session.
- `personality` and `startScript` can be **overridden per session**.
- Embed via the Runway widget / React integration or LiveKit Agents.
- Pricing: `gwm1_avatars` ≈ 2 credits upfront + 2 credits / 6 seconds.

## Notes
- The persona rationale lives in `persona.md`.
- Best likeness comes from a real voice clone + the original photo. Magnific upscaling is
  generative and can subtly alter a real face — keep `todd_source.jpeg` as the canonical
  source unless an upscale clearly preserves his likeness.
</content>
