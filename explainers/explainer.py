#!/usr/bin/env python3
"""Make a ~90-second animated explainer: one character, one audience, one topic, end to end.

    python3 explainer.py check  episodes/<topic>.json   # validate the script against the formula; spends nothing
    python3 explainer.py make   episodes/<topic>.json   # render, QC, re-roll, assemble, verify
    python3 explainer.py verify episodes/<topic>.json   # re-run the final checks on an assembled episode
    python3 explainer.py voice-ref <clip.mp4> <start_s> <end_s> <characters/x/voice.mp3>   # build a voice reference
    python3 explainer.py bed "<music description>" <music/name.mp3>                       # build a music bed

Start with PLAYBOOK.md. An episode names a CHARACTER (characters/<name>/character.json: look, voice, model) and an
AUDIENCE (audiences/<name>.json: who is being spoken to, and how their names are spelled and heard). The code knows
neither; swapping either is a data change.

THE MECHANISM, and why it is shaped like this:

  Every scene is ONE Seedance generation that produces picture, voice and sound effects TOGETHER.
  - Lips match the voice because the same model makes both. (The first video generated silent picture and laid
    TTS over it: the mouth moved without knowing the words, and the Commander called it disjointing.)
  - Sound effects land on the action for the same reason. (The first video cued effects to the narration's
    words; a rocket that launches half a second after "blast off" got its whoosh at the wrong moment.)
  - The voice is held constant across scenes by `referenceAudio` (a clean sample of the character's voice) and the
    character by `promptImage` as an UNPOSITIONED reference — Runway refuses referenceAudio together with
    first/last-frame keyframes.
  - Music is the one thing NOT made per scene: every clip is told "no background music" and one bed runs under the
    whole episode, ducked under the dialogue, so the score does not change at every cut.

QC is automated and gates delivery. Each scene's own audio is transcribed and compared with its line; the audience's
names are checked in the first and last scenes; a failing scene is re-rolled with a new seed. After assembly the
finished file is checked again as a whole (script, names, length, loudness) and a contact sheet is written for a
human-style look at the pictures, which no automated check covers.
"""
from __future__ import annotations

import concurrent.futures as cf
import difflib
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FF, FP, WHISPER = "/usr/local/bin/ffmpeg", "/usr/local/bin/ffprobe", "/usr/local/bin/whisper-cli"
WHISPER_MODEL = os.path.join(HERE, "models", "ggml-base.en.bin")

PROMPT_LIMIT = 1000        # Runway rejects promptText over 1000 characters
MAX_WORDS_PER_SCENE = 34   # ~15 s of unhurried speech; more and the model gabbles to fit the clip
SCENE_SECONDS = 15         # a good beat length for small children
MIN_SCENES, MAX_SCENES = 4, 16   # 1-4 minutes. Past four, a three-year-old has left the room
MAX_PARALLEL = 16          # Runway's tier allows 20 concurrent tasks; leave headroom for anything else running
# Credits per second of video. estimate_credits() prices an unknown model at the HIGHEST rate on purpose.
CREDITS_PER_SECOND = {"seedance2_5": 30, "seedance2": 40}
# seedance2_5 unless a character says otherwise. Measured 2026-09-26 with Syl: seedance2 was refused
# (SAFETY.OUTPUT.THIRD_PARTY) three times; seedance2_5 never was, made the voice the Commander likes, and costs
# 30 cr/s not 40. A refusal is decided by the LIKENESS, so it is a property of the character, not of the kit.
DEFAULT_MODEL = "seedance2_5"
DEFAULT_RATIO = "834:1112"  # portrait: a phone or tablet held by a child
MIN_LINE_MATCH = 0.72      # transcript-vs-script similarity below this = the scene is re-rolled
MIN_EPISODE_MATCH = 0.80   # the whole finished mix against the whole script
TARGET_LUFS, LUFS_TOLERANCE = -16.0, 1.5
MAX_ATTEMPTS = 3           # per scene, covering moderation refusals and bad takes
SHARE_LIMIT_BYTES = 29 * 1024 * 1024  # SendUserFile refuses files over 30 MB
TAIL = " No background music. No text, letters or numbers anywhere."

# whisper writes a correctly spoken "number six" as "Number 6"; comparing digits to words would reject good takes.
_NUMBER_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                 "sixteen seventeen eighteen nineteen twenty").split()
_SYNONYMS = {"okay": "ok"}


# ----------------------------------------------------------------------------- loading

def read_json(path: str):
    with open(path) as f:
        return json.load(f)


def write_json(obj, path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def load_cast(episode: dict, root: str = HERE) -> tuple[dict, dict]:
    """The episode's character and audience, with every file path made absolute and checked to exist.

    A character's reference image and voice live in its own folder; its music bed lives in the shared music/ folder
    (several characters may share one). Raises FileNotFoundError naming the missing thing.
    """
    cdir = os.path.join(root, "characters", str(episode.get("character", "")))
    cfile = os.path.join(cdir, "character.json")
    afile = os.path.join(root, "audiences", f"{episode.get('audience', '')}.json")
    for f, what in ((cfile, f"character '{episode.get('character')}'"), (afile, f"audience '{episode.get('audience')}'")):
        if not os.path.exists(f):
            raise FileNotFoundError(f"{what}: no {os.path.relpath(f, root)}")
    character = read_json(cfile)
    character.setdefault("model", DEFAULT_MODEL)
    character.setdefault("ratio", DEFAULT_RATIO)
    character.setdefault("pronoun", "They")
    paths = {"reference_image": cdir, "voice_reference": cdir, "music": os.path.join(root, "music")}
    music = episode.get("music")
    if music:
        character["music"] = music
    for key, base in paths.items():
        if not character.get(key):
            raise FileNotFoundError(f"character '{episode.get('character')}': '{key}' is not set in character.json")
        character[key] = os.path.join(base, character[key])
        if not os.path.exists(character[key]):
            raise FileNotFoundError(f"character '{episode.get('character')}': {key} {os.path.relpath(character[key], root)} is missing")
    return character, read_json(afile)


def load_guests(episode: dict, root: str = HERE) -> list[dict]:
    """Characters who APPEAR but do not speak (e.g. the child a video is for, drawn as a cartoon). A guest needs a
    `look` and a `reference_image`; it has no voice, and the host does all the talking."""
    guests = []
    for name in episode.get("guests") or []:
        gdir = os.path.join(root, "characters", name)
        gfile = os.path.join(gdir, "character.json")
        if not os.path.exists(gfile):
            raise FileNotFoundError(f"guest '{name}': no {os.path.relpath(gfile, root)}")
        guest = read_json(gfile)
        guest["reference_image"] = os.path.join(gdir, guest.get("reference_image", "reference.png"))
        if not os.path.exists(guest["reference_image"]):
            raise FileNotFoundError(f"guest '{name}': reference image {guest['reference_image']} is missing")
        guests.append(guest)
    return guests


# ----------------------------------------------------------------------------- pure logic

def words(text: str) -> list[str]:
    """Normalised word tokens: lower case, hyphens split, digits 0-20 as words, spelling variants folded."""
    toks = re.findall(r"[a-z0-9']+", text.lower().replace("—", " ").replace("-", " "))
    out = []
    for t in toks:
        if t.isdigit() and int(t) < len(_NUMBER_WORDS):
            t = _NUMBER_WORDS[int(t)]
        out.append(_SYNONYMS.get(t, t))
    return out


def spoken_words(line: str) -> int:
    """How many words the character has to say — the budget that decides whether a scene fits its 15 s."""
    return len(words(line))


def build_prompt(scene: dict, character: dict, guests: list[dict] = ()) -> str:
    """The full promptText for one scene. Raises if it would breach Runway's 1000-character limit.
    Order matters: host, then guests in reference-image order, so "the second reference image" means what it says."""
    prompt = (character["look"] + "".join(g["look"] for g in guests) + scene["action"].strip() + f' {character.get("pronoun", "They")} speaks to the viewer: "'
              + scene["line"].strip() + '"' + " Sound effects: " + scene["sfx"].strip().rstrip(".") + "." + TAIL)
    if len(prompt) > PROMPT_LIMIT:
        raise ValueError(f"scene {scene.get('id')}: prompt is {len(prompt)} chars, limit {PROMPT_LIMIT} — shorten the action")
    return prompt


def validate(episode: dict, character: dict, audience: dict, guests: list[dict] = ()) -> list[str]:
    """Every rule a script can break before anything is spent. Empty list = ready to render."""
    problems = []
    scenes = episode.get("scenes") or []
    if not MIN_SCENES <= len(scenes) <= MAX_SCENES:
        problems.append(f"{len(scenes)} scenes; use {MIN_SCENES}-{MAX_SCENES} (6 for 90 seconds, 12 for three minutes)")
    seen = set()
    for i, sc in enumerate(scenes):
        sid = sc.get("id", f"#{i + 1}")
        if sid in seen:
            problems.append(f"{sid}: duplicate scene id — takes are filed by id and would overwrite each other")
        seen.add(sid)
        for key in ("id", "line", "action", "sfx", "fact_check"):
            if not str(sc.get(key, "")).strip():
                problems.append(f"{sid}: missing '{key}'")
        if sc.get("line"):
            n = spoken_words(sc["line"])
            if n > MAX_WORDS_PER_SCENE:
                problems.append(f"{sid}: {n} words, max {MAX_WORDS_PER_SCENE} — the character will rush to fit 15 s")
            if re.search(r"\d", sc["line"]):
                problems.append(f"{sid}: digits in the line — write numbers as words so they are spoken, not read")
        try:
            if all(sc.get(k) for k in ("line", "action", "sfx")):
                build_prompt(sc, character, guests)
        except ValueError as e:
            problems.append(str(e))
    if scenes:
        spoken = [n["spoken"] for n in audience.get("names", [])]
        for where, sc in (("first", scenes[0]), ("last", scenes[-1])):
            missing = [n for n in spoken if n not in sc.get("line", "")]
            if missing:
                problems.append(f"{where} scene must greet every child by name; missing {', '.join(missing)} "
                                f"(spell them exactly as in the audience file)")
    return problems


def scene_body(scene: dict, character: dict, guests: list[dict], data_uri) -> dict:
    """The image_to_video request for one scene, minus the seed.

    Every image is an UNPOSITIONED reference (host first, then guests): Runway refuses referenceAudio alongside
    first/last keyframes, and the voice reference is what keeps the host sounding like herself. Only the host has a
    voice; guests are seen, not heard.
    """
    return {"model": character["model"],
            "promptImage": [{"uri": data_uri(c["reference_image"])} for c in (character, *guests)],
            "promptText": build_prompt(scene, character, guests), "ratio": character["ratio"],
            "duration": SCENE_SECONDS, "audio": True,
            "referenceAudio": [{"type": "audio", "uri": data_uri(character["voice_reference"])}]}


def estimate_credits(episode: dict, character: dict) -> int:
    """First-take cost. Re-rolls cost the same again per scene."""
    rate = CREDITS_PER_SECOND.get(character.get("model"), max(CREDITS_PER_SECOND.values()))
    return len(episode.get("scenes") or []) * SCENE_SECONDS * rate


def line_match(expected: str, heard: str) -> float:
    """0..1 similarity between the script and what was actually said."""
    a, b = words(expected), words(heard)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def names_missing(transcript: str, audience: dict) -> list[str]:
    """The audience names (as spelled in the script) that the transcript does not contain in any heard form."""
    t = transcript.lower()
    return [n["spoken"] for n in audience.get("names", []) if not any(h in t for h in n["heard"])]


def scene_verdict(scene: dict, transcript: str, is_bookend: bool, audience: dict) -> tuple[bool, str]:
    """Does this take pass QC? Returns (ok, reason)."""
    score = line_match(scene["line"], transcript)
    if score < MIN_LINE_MATCH:
        return False, f"said the wrong words (match {score:.2f})"
    if is_bookend:
        missing = names_missing(transcript, audience)
        if missing:
            return False, f"names not heard clearly: {', '.join(missing)}"
    return True, f"match {score:.2f}"


def final_problems(episode: dict, transcript: str, seconds: float, lufs: float, audience: dict) -> list[str]:
    """What is wrong with the FINISHED file. A scene can pass alone and the mix still bury it, so this is not redundant."""
    problems = []
    script = " ".join(s["line"] for s in episode["scenes"])
    score = line_match(script, transcript)
    if score < MIN_EPISODE_MATCH:
        problems.append(f"the finished mix does not say the script (match {score:.2f}, need {MIN_EPISODE_MATCH})")
    missing = names_missing(transcript, audience)
    if missing:
        problems.append(f"names not heard in the finished mix: {', '.join(missing)}")
    expected = len(episode["scenes"]) * SCENE_SECONDS
    if not 0.9 * expected <= seconds <= 1.1 * expected:
        problems.append(f"{seconds:.1f} seconds, expected about {expected}")
    if abs(lufs - TARGET_LUFS) > LUFS_TOLERANCE:
        problems.append(f"loudness {lufs:.1f} LUFS, target {TARGET_LUFS}")
    return problems


# ----------------------------------------------------------------------------- side effects

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path: str) -> float:
    return float(_run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout.strip())


def transcribe(media: str, work: str) -> str:
    """Timestamped mode ONLY: whisper-cli's -nt mode silently drops whole segments."""
    wav = os.path.join(work, os.path.basename(media) + ".16k.wav")
    _run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", media, "-vn", "-ar", "16000", "-ac", "1", wav])
    out = _run([WHISPER, "-m", WHISPER_MODEL, "-f", wav, "-np"]).stdout
    return " ".join(re.sub(r"^\[.*?\]\s*", "", ln).strip() for ln in out.splitlines() if ln.strip())


def loudness(path: str) -> float:
    """Integrated loudness (LUFS) from ffmpeg's ebur128 summary, which it prints on stderr."""
    err = _run([FF, "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"]).stderr
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    if not found:
        raise RuntimeError("ebur128 printed no integrated loudness")
    return float(found[-1])


def render_scene(rw, scene: dict, character: dict, guests: list[dict], audience: dict, work: str, is_bookend: bool,
                 log) -> dict:
    """Generate one scene, transcribe it, and re-roll until it passes QC or attempts run out.

    A take already on disk is re-QC'd, never re-rendered: a fix to a QC rule must cost nothing to apply to takes
    already paid for. (The first time the name gate was wrong it rejected three good takes, ~1,350 credits.)
    """
    body = scene_body(scene, character, guests, rw.data_uri)
    history = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        body["seed"] = random.randint(1, 4_000_000_000)
        dest = os.path.join(work, f"{scene['id']}.take{attempt}.mp4")
        t0 = time.time()
        on_disk = os.path.exists(dest)
        if not on_disk:
            try:
                rw.run("image_to_video", body, dest)
            except Exception as e:                  # moderation refusal or transient failure: re-roll
                history.append(f"take {attempt}: {str(e)[:160]}")
                log(f"  {scene['id']}: take {attempt} failed ({str(e)[:100]}) — re-rolling")
                continue
        heard = transcribe(dest, work)
        ok, why = scene_verdict(scene, heard, is_bookend, audience)
        took = "on disk" if on_disk else f"{(time.time() - t0) / 60:.1f} min"
        history.append(f"take {attempt} ({took}): {why}")
        log(f"  {scene['id']}: take {attempt} ({took}) {'PASS' if ok else 'REJECT'} — {why}")
        if ok:
            return {"id": scene["id"], "clip": dest, "heard": heard, "history": history, "ok": True}
    return {"id": scene["id"], "clip": None, "heard": "", "history": history, "ok": False}


def assemble(clips: list[str], music: str, out: str) -> None:
    """Concatenate the scenes WITH their own audio, lay one music bed under the lot, duck it under the dialogue,
    and normalise to -16 LUFS."""
    ins, fc = [], []
    for i, c in enumerate(clips):
        ins += ["-i", c]
        fc.append(f"[{i}:v]scale=834:1112,fps=24,setsar=1,format=yuv420p[v{i}];"
                  f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=0:{duration(c):.3f}[a{i}]")
    n = len(clips)
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][dlg]")
    total = sum(duration(c) for c in clips)
    ins += ["-stream_loop", "-1", "-i", music]
    fc.append(f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
              f"volume=0.22,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.3f}:d=2.5[bed]")
    fc.append("[dlg]asplit=2[dlg1][key]")
    fc.append("[bed][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[ducked]")
    fc.append(f"[dlg1][ducked]amix=inputs=2:normalize=0:duration=first,loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11[a]")
    _run([FF, "-hide_banner", "-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(fc),
          "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])


def contact_sheet(video: str, dest: str, seconds: float) -> None:
    """Twelve frames across the episode in one image: the look that catches lettering, extra limbs and drift."""
    _run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", video,
          "-vf", f"fps=12/{seconds:.3f},scale=278:-1,tile=4x3", "-frames:v", "1", dest])


def share_copy(video: str) -> str:
    """The file to send: the master if it fits the SendUserFile limit, else the lightest re-encode that does.
    A three-minute episode does not fit at CRF 23, so this steps the quality down only as far as it must."""
    if os.path.getsize(video) <= SHARE_LIMIT_BYTES:
        return video
    small = video.replace(".mp4", "-share.mp4")
    for crf in (26, 28, 30, 32):
        _run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-c:v", "libx264", "-crf", str(crf),
              "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart", small])
        if os.path.getsize(small) <= SHARE_LIMIT_BYTES:
            return small
    raise RuntimeError(f"{small} is still over {SHARE_LIMIT_BYTES} bytes at CRF 32; send it another way")


def paths_for(episode_path: str) -> tuple[str, str, str]:
    name = os.path.splitext(os.path.basename(episode_path))[0]
    work = os.path.join(HERE, "out", name)
    return name, work, os.path.join(HERE, "out", f"{name}.mp4")


def verify(episode_path: str, log=print) -> int:
    """Check the assembled episode as a whole and write out/<name>/report.json and contact.jpg."""
    episode = read_json(episode_path)
    _, audience = load_cast(episode)
    name, work, out = paths_for(episode_path)
    seconds, lufs = duration(out), loudness(out)
    heard = transcribe(out, work)
    problems = final_problems(episode, heard, seconds, lufs, audience)
    sheet = os.path.join(work, "contact.jpg")
    contact_sheet(out, sheet, seconds)
    share = share_copy(out)
    report = {"episode": name, "file": out, "share": share, "seconds": round(seconds, 1), "lufs": lufs,
              "megabytes": round(os.path.getsize(share) / 1e6, 1), "contact_sheet": sheet,
              "transcript": heard, "problems": problems}
    write_json(report, os.path.join(work, "report.json"))
    log(f"verify: {seconds:.1f} s, {lufs:.1f} LUFS, {report['megabytes']} MB — "
        + ("PASS" if not problems else "FAIL: " + "; ".join(problems)))
    log(f"  LOOK AT {sheet} before sending: no automated check sees lettering, extra creatures or a drifting character.")
    return 0 if not problems else 1


def make(episode_path: str) -> int:
    t_start = time.time()
    log = lambda m: print(f"[{(time.time() - t_start) / 60:5.1f} min] {m}", flush=True)
    episode = read_json(episode_path)
    character, audience = load_cast(episode)
    guests = load_guests(episode)
    problems = validate(episode, character, audience, guests)
    if problems:
        print("NOT RENDERING — the script breaks the formula:\n  " + "\n  ".join(problems))
        return 2
    sys.path.insert(0, HERE)
    import rw  # noqa: E402  (needs RUNWAYML_API_SECRET in the environment)
    name, work, out = paths_for(episode_path)
    os.makedirs(work, exist_ok=True)
    scenes = episode["scenes"]
    log(f"{episode.get('title', name)}: {len(scenes)} scenes, {character['name']} for {audience['name']}, "
        f"{character['model']}, rendering in parallel")
    with cf.ThreadPoolExecutor(min(len(scenes), MAX_PARALLEL)) as pool:
        futs = [pool.submit(render_scene, rw, sc, character, guests, audience, work, i in (0, len(scenes) - 1), log)
                for i, sc in enumerate(scenes)]
        results = [f.result() for f in futs]
    write_json(results, os.path.join(work, "qc.json"))
    failed = [r["id"] for r in results if not r["ok"]]
    if failed:
        log(f"NOT DELIVERED — scenes failed QC after {MAX_ATTEMPTS} takes: {failed}. See {work}/qc.json; "
            f"rewrite those scenes (PLAYBOOK.md, 'When a scene keeps failing') and run make again.")
        return 1
    log("assembling")
    assemble([r["clip"] for r in results], character["music"], out)
    status = verify(episode_path, log)
    log(f"{'done' if status == 0 else 'ASSEMBLED BUT FAILED VERIFY'}: {out}")
    return status


# ----------------------------------------------------------------------------- building a new character or bed

def voice_ref(clip: str, start: float, end: float, dest: str) -> int:
    """Cut the character's speech out of a clip you like and strip the music/effects under it (voice_isolation).
    10-15 s of clean, expressive speech is plenty; the reference steers the generated voice, it does not replace it."""
    sys.path.insert(0, HERE)
    import rw  # noqa: E402
    raw = dest.replace(".mp3", ".raw.mp3")
    _run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-to", str(end), "-i", clip,
          "-vn", "-ac", "1", "-b:a", "192k", raw])
    rw.run("voice_isolation", {"model": "eleven_voice_isolation", "audioUri": rw.data_uri(raw)}, dest)
    os.remove(raw)
    print(f"voice reference: {dest} ({duration(dest):.1f} s). Listen to it before using it.")
    return 0


def bed(description: str, dest: str, seconds: float = 22.0) -> int:
    """Generate a loopable instrumental bed and prove it has no vocals (a sung word under dialogue is a disaster)."""
    sys.path.insert(0, HERE)
    import rw  # noqa: E402
    prompt = description.rstrip(".") + ". Instrumental only, no vocals, no singing, seamless loop."
    rw.run("sound_effect", {"model": "eleven_text_to_sound_v2", "promptText": prompt[:1000], "duration": seconds,
                            "loop": True}, dest)
    heard = words(transcribe(dest, os.path.dirname(dest) or "."))
    if heard and heard not in (["music"],):
        print(f"REJECT — whisper hears words in the bed: {' '.join(heard)[:120]}. Run it again.")
        return 1
    print(f"music bed: {dest} ({duration(dest):.1f} s), no vocals heard.")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] in ("check", "make", "verify"):
        if args[0] == "make":
            sys.exit(make(args[1]))
        if args[0] == "verify":
            sys.exit(verify(args[1]))
        ep = read_json(args[1])
        ch, aud = load_cast(ep)
        p = validate(ep, ch, aud, load_guests(ep))
        print(f"OK — ready to render ({len(ep['scenes'])} scenes = {len(ep['scenes']) * SCENE_SECONDS} s, {ch['name']} "
              f"for {aud['name']}, ~{estimate_credits(ep, ch):,} credits first-take)" if not p else "PROBLEMS:\n  " + "\n  ".join(p))
        sys.exit(0 if not p else 2)
    if len(args) == 5 and args[0] == "voice-ref":
        sys.exit(voice_ref(args[1], float(args[2]), float(args[3]), args[4]))
    if len(args) == 3 and args[0] == "bed":
        sys.exit(bed(args[1], args[2]))
    sys.exit(__doc__)
