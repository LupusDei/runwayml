# PLAYBOOK — making a 90-second animated explainer, for any agent

You are making a short, funny, true video in which a **character** talks to an **audience** (usually named
children) about a **topic**. You write one JSON file; `explainer.py` renders it, checks it, and assembles it. Expect
about **15 minutes** end to end and about **2,700 credits (~$27)** for a first-take episode.

Read **FORMULA.md** before writing — it is what makes the episode funny rather than merely correct.

## 0. Setup (once per machine)

```sh
cd ~/code/ai/runwayml/explainers
set -a && . ../.env && set +a            # RUNWAYML_API_SECRET — never print it, never commit it
python3 -m unittest test_explainer       # 29 tests, no network
```
Needs `/usr/local/bin/ffmpeg`, `ffprobe`, `whisper-cli`, and `models/ggml-base.en.bin`
(`curl -L -o models/ggml-base.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin`).

## 1. Pick the cast — or add to it

| What | Where | What is in it |
|---|---|---|
| Character | `characters/<name>/character.json` | `look` (prompt prefix: the character, any companion, the world, the art style), `pronoun`, `reference_image`, `voice_reference`, `music`, optional `model` and `ratio` |
| Audience | `audiences/<name>.json` | each name as the model should **say** it (`spoken`, phonetic) and every way whisper **writes** a correct pronunciation (`heard`) |
| Music | `music/<name>.mp3` | one loopable instrumental bed, shared by characters |

Committed: character **syl** (starlight woman plus a tiny bat-winged unicorn), the fictional audience **example**,
and `episodes/example.json`.

**This repository is PUBLIC. Real children stay local.** Real audiences, episodes naming real people, and guest
characters drawn from real photos are all gitignored. Don't force-add them. A real child's name, age or face
does not belong on GitHub. Only `example` files and fictional characters are committed.

**A new character** needs three things, and each has a command or a rule:
1. **A reference image.** Use a frame the owner already loves (`ffmpeg -ss 6 -i clip.mp4 -frames:v 1 reference.png`).
   Do not invent or redesign someone's established character; their likeness is theirs.
2. **A voice reference.** Take 10–15 s of the character speaking clearly, from a clip whose voice the owner likes:
   `python3 explainer.py voice-ref clip.mp4 2.9 13.4 characters/<name>/voice.mp3`.
   This cuts the clip and strips the music out with `voice_isolation`. **Listen to the result.**
   Designed and preset TTS voices were all rejected for Syl; her own native generated voice won.
3. **A `look` sentence.** It is prepended to every scene prompt. Name every trait that drifts, such as wing type,
   hair colour or outfit, because what goes unsaid drifts between scenes. Keep it under about 300 characters;
   the action, the line and the sound effects share the 1000-character limit with it.

Then run `check` on a two-scene test episode and render **one** scene before a full episode. Some likenesses get
moderation refusals on one model and not on another (Syl: `seedance2` refused her three times; `seedance2_5`
never did). Set `model` in the character file once you know which model works.

**A new audience:** write `spoken` phonetically ("Mee-ra", "Thee-oh"). Leave `heard` empty, render the first
scene, read `out/<ep>/qc.json` to see what whisper wrote, and add those spellings. Never lower the match
threshold to get a name through.

**A new music bed:** `python3 explainer.py bed "playful plucked strings and soft glockenspiel, gentle, bouncy" music/<name>.mp3`.
It rejects the bed if whisper hears words in it.

**A guest** is a character who appears but never speaks, such as the child a video is for, drawn as a cartoon.
It needs a `characters/<name>/character.json` with a `look` and a `reference_image`, and no voice. List it in the
episode as `"guests": ["<name>"]`.
- Its reference goes to Runway after the host's, so its `look` must say "from the second reference image".
- To draw a real child: send `gen4_image` a **face-only crop** of one photo, tagged, plus the host's reference for
  style. Say "healthy, no marks" and dress them.
- Make three variants and pick one. The photo goes to Runway once; every scene uses the cartoon.

## 2. Write the episode

Copy `episodes/example.json`. Use one scene per 15-second beat, six scenes in all. Each scene has:
- `id`: the takes are filed under it.
- `line`: exactly what the character says. Keep it to 34 words or fewer, with no digits.
- `action`: what we see, including the companion gag.
- `sfx`: the sounds the action makes.

Check the facts. Everything the character says must be true. Kid-famous myths (Washington's wooden teeth,
JQA's alligator) are the trap: when a story is disputed, pick a different fact.

```sh
python3 explainer.py check episodes/<topic>.json      # free; fix every problem it lists
```

## 3. Make it

```sh
python3 explainer.py make episodes/<topic>.json > out/<topic>.log 2>&1   # run in the background
```

It does the following:
1. Renders all scenes in parallel.
2. Transcribes each take and compares it with the line.
3. Checks the names in the first and last scenes.
4. Re-rolls any failures, up to 3 takes per scene.
5. Assembles the passing takes with the ducked music bed at −16 LUFS.
6. Runs `verify`.

A take already on disk is **re-checked, never re-rendered**, so re-running `make` after you fix a QC rule or
one scene costs nothing for the scenes that already passed. To redo a scene you don't like, delete its
`out/<topic>/<id>.take*.mp4` and run `make` again.

## 4. Look before you send

`verify` checks the whole file: the script against the transcript, the names, the length and the loudness.
It then writes `out/<topic>/report.json` and **`out/<topic>/contact.jpg`**. **Open the contact sheet.** No
automated check sees these:
- lettering or gibberish text;
- extra creatures or extra limbs;
- a character whose outfit, hair or companion has drifted;
- anything scary.

If a frame is wrong, delete that scene's passing take and run `make` again.

Send `report.json` → `share`, which is under 30 MB and re-encoded only if needed.

## When a scene keeps failing

`out/<topic>/qc.json` has every take's history and what whisper heard. Each failure has a usual fix:

| Failure | Fix |
|---|---|
| **Wrong words**, match below 0.72 | The line is too long or tongue-twisty. Cut words; split compound names out of long sentences. |
| **Names not heard** | Check `heard` in the audience file first: the take may be right and the list incomplete. That cost ~1,350 credits once. |
| **`SAFETY.OUTPUT.THIRD_PARTY`** | The refusal follows the likeness, not the words. Try the character's other model. Don't rephrase to sneak past a classifier. Refused jobs are still charged. |
| **Bookend merges** | "Bye" before a vowel-initial name merged into one word. Put a word between the vowels: "See you soon, Ava!" |

## Costs and limits worth knowing

| Item | Figure |
|---|---|
| `seedance2_5` | 30 cr/s, so a 15 s scene is 450 credits. A re-roll costs the same. |
| Render time | 4–7 min per scene. Scenes run in parallel (org tier: 20 concurrent). |
| Runway output URLs | Expire after 24 h. `make` downloads immediately. |
| `promptText` | 1000 characters maximum. `check` computes every prompt. |
