# explainers — 90-second animated explainer videos, one command

A character tells an audience about a topic, in six 15-second scenes. Picture, lip-synced voice and sound effects
come out of **one** generation per scene, so they are in sync by construction. Whisper QC re-rolls any scene
that says the wrong words or garbles a name. A final verify checks the finished file as a whole.

```sh
set -a && . ../.env && set +a
python3 explainer.py check episodes/example.json      # free
python3 explainer.py make  episodes/<topic>.json      # ~15 min, ~2,700 credits
python3 -m unittest test_explainer
```

- **PLAYBOOK.md**: the step-by-step, including how to add a character, a voice, an audience or a music bed.
- **FORMULA.md**: how to write an episode that is funny first and true always.
- `characters/`, `audiences/`, `music/`, `episodes/` hold data; `explainer.py` knows none of it.

**Media is not committed** (`*.mp3`, `*.png`, `models/`, `out/`). The files are local to this machine;
PLAYBOOK §1 says how each one is rebuilt.

**This repository is public.** Real audiences, real episodes and guests drawn from real photos are
gitignored and local only (PLAYBOOK §1). `episodes/example.json` and `audiences/example.json` are fictional.

The first, `productions/syl-first-eight-elements`, used an older TTS-over-video method, now retired.
