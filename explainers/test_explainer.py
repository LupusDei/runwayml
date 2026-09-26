"""Tests for the pure logic of explainer.py. No network, no ffmpeg: run with `python3 -m unittest test_explainer`."""
import copy
import json
import os
import tempfile
import unittest

import explainer as ex

CHAR = {"name": "Syl", "pronoun": "She", "look": "Syl, a glowing starlight woman. ", "model": "seedance2_5",
        "ratio": "834:1112", "reference_image": "/x/reference.png", "voice_reference": "/x/voice.mp3",
        "music": "/x/bed.mp3"}
# Fictional children. Real audiences live in gitignored files: this repository is public.
AUD = {"name": "Mira and Theo", "names": [
    {"spoken": "Mee-ra", "heard": ["mira", "meera", "myra"]},
    {"spoken": "Thee-oh", "heard": ["theo", "teo", "tio"]}]}
GOOD = {"character": "syl", "audience": "mira-and-theo", "scenes": [
    {"id": "01", "line": "Mee-ra! Thee-oh! Hop in, we are flying past all eight planets!", "action": "She waves.", "sfx": "rocket whoosh", "fact_check": "eight planets: IAU 2006"},
    {"id": "02", "line": "Venus is the hottest planet of all.", "action": "They fly past Venus.", "sfx": "sizzle", "fact_check": "NASA planet fact sheets"},
    {"id": "03", "line": "Earth is our home.", "action": "They wave at Earth.", "sfx": "birdsong", "fact_check": "NASA planet fact sheets"},
    {"id": "04", "line": "Mars is red and dusty.", "action": "Red dust puffs.", "sfx": "wind", "fact_check": "NASA planet fact sheets"},
    {"id": "05", "line": "See you soon, Mee-ra! See you soon, Thee-oh!", "action": "She waves goodbye.", "sfx": "twinkle", "fact_check": "NASA planet fact sheets"},
]}


def problems(episode=GOOD, character=CHAR, audience=AUD):
    return ex.validate(episode, character, audience)


def heard_script():
    """The whole GOOD script as whisper would write it back."""
    return " ".join(s["line"] for s in GOOD["scenes"]).replace("Mee-ra", "Myra").replace("Thee-oh", "Theo")


class ValidateTest(unittest.TestCase):
    def test_should_accept_a_script_that_follows_the_formula(self):
        self.assertEqual(problems(), [])

    def test_should_reject_a_line_too_long_to_say_in_fifteen_seconds(self):
        bad = copy.deepcopy(GOOD)
        bad["scenes"][1]["line"] = "word " * (ex.MAX_WORDS_PER_SCENE + 1)
        self.assertTrue(any("max" in p for p in problems(bad)))

    def test_should_reject_digits_because_they_get_read_not_spoken(self):
        bad = copy.deepcopy(GOOD)
        bad["scenes"][2]["line"] = "There are 8 planets."
        self.assertTrue(any("digits" in p for p in problems(bad)))

    def test_should_require_every_audience_name_in_the_first_and_last_scene(self):
        bad = copy.deepcopy(GOOD)
        bad["scenes"][-1]["line"] = "See you soon, Mee-ra!"
        found = problems(bad)
        self.assertTrue(any("last scene" in p and "Thee-oh" in p for p in found), found)

    def test_should_take_the_names_from_the_audience_not_from_the_code(self):
        other = {"name": "Sam", "names": [{"spoken": "Sam", "heard": ["sam"]}]}
        ep = copy.deepcopy(GOOD)
        ep["scenes"][0]["line"] = "Hi Sam! Let's go!"
        ep["scenes"][-1]["line"] = "See you soon, Sam!"
        self.assertEqual(problems(ep, audience=other), [])

    def test_should_not_count_a_name_hidden_inside_another_word_as_a_greeting(self):
        al = {"name": "Al", "names": [{"spoken": "Al", "heard": ["al"]}]}
        ep = copy.deepcopy(GOOD)
        ep["scenes"][0]["line"] = "Also, we will build a robot!"
        ep["scenes"][-1]["line"] = "See you soon, Al!"
        self.assertTrue(any("first scene" in p for p in problems(ep, audience=al)))

    def test_should_reject_too_few_scenes_for_ninety_seconds(self):
        self.assertTrue(problems({"scenes": GOOD["scenes"][:2]}))

    def test_should_report_a_missing_field_instead_of_crashing(self):
        bad = copy.deepcopy(GOOD)
        del bad["scenes"][1]["sfx"]
        self.assertTrue(any("missing 'sfx'" in p for p in problems(bad)))

    def test_should_accept_a_three_minute_episode_of_twelve_scenes(self):
        long = copy.deepcopy(GOOD)
        middle = [dict(GOOD["scenes"][1], id=f"m{i}") for i in range(10)]
        long["scenes"] = [GOOD["scenes"][0], *middle, GOOD["scenes"][-1]]
        self.assertEqual(problems(long), [])

    def test_should_reject_more_scenes_than_a_small_child_will_sit_through(self):
        long = copy.deepcopy(GOOD)
        middle = [dict(GOOD["scenes"][1], id=f"m{i}") for i in range(ex.MAX_SCENES)]
        long["scenes"] = [GOOD["scenes"][0], *middle, GOOD["scenes"][-1]]
        self.assertTrue(any("scenes" in p for p in problems(long)))

    def test_should_require_every_scene_to_say_how_its_facts_were_checked(self):
        bad = copy.deepcopy(GOOD)
        del bad["scenes"][2]["fact_check"]
        self.assertTrue(any("fact_check" in p for p in problems(bad)))

    def test_should_reject_duplicate_scene_ids_because_takes_are_filed_by_id(self):
        bad = copy.deepcopy(GOOD)
        bad["scenes"][2]["id"] = "02"
        self.assertTrue(any("duplicate" in p for p in problems(bad)))


class PromptTest(unittest.TestCase):
    def test_should_put_the_line_in_quotes_so_the_model_speaks_it(self):
        self.assertIn('"Venus is the hottest planet of all."', ex.build_prompt(GOOD["scenes"][1], CHAR))

    def test_should_describe_the_character_from_its_profile(self):
        p = ex.build_prompt(GOOD["scenes"][1], dict(CHAR, look="Pip, a small robot. ", pronoun="It"))
        self.assertTrue(p.startswith("Pip, a small robot."))
        self.assertIn('It speaks to the viewer: "', p)

    def test_should_forbid_music_and_lettering_in_every_scene(self):
        p = ex.build_prompt(GOOD["scenes"][1], CHAR)
        self.assertIn("No background music", p)
        self.assertIn("No text", p)

    def test_should_refuse_a_prompt_over_runways_limit(self):
        with self.assertRaises(ValueError):
            ex.build_prompt(dict(GOOD["scenes"][1], action="x" * ex.PROMPT_LIMIT), CHAR)


GUEST = {"name": "Pip", "look": "Pip, the cartoon robot from the second reference image; he never speaks. ",
         "reference_image": "/x/pip.png"}


class GuestTest(unittest.TestCase):
    def test_should_describe_every_guest_after_the_host(self):
        p = ex.build_prompt(GOOD["scenes"][1], CHAR, [GUEST])
        self.assertLess(p.index("Syl, a glowing"), p.index("Pip, the cartoon robot"))
        self.assertLess(p.index("Pip, the cartoon robot"), p.index("They fly past Venus."))

    def test_should_send_the_host_reference_first_and_each_guest_after_it(self):
        body = ex.scene_body(GOOD["scenes"][1], CHAR, [GUEST], data_uri=lambda path: "uri:" + path)
        self.assertEqual([i["uri"] for i in body["promptImage"]], ["uri:/x/reference.png", "uri:/x/pip.png"])
        self.assertNotIn("position", body["promptImage"][0])   # positioned keyframes cannot take referenceAudio

    def test_should_keep_only_the_host_voice(self):
        body = ex.scene_body(GOOD["scenes"][1], CHAR, [GUEST], data_uri=lambda path: "uri:" + path)
        self.assertEqual(body["referenceAudio"], [{"type": "audio", "uri": "uri:/x/voice.mp3"}])

    def test_should_count_guest_looks_against_the_prompt_limit(self):
        long_guest = dict(GUEST, look="x" * (ex.PROMPT_LIMIT - 150))
        self.assertTrue(any("chars" in p for p in ex.validate(GOOD, CHAR, AUD, [long_guest])))

    def test_should_load_a_guest_without_a_voice(self):
        with tempfile.TemporaryDirectory() as root:
            gdir = os.path.join(root, "characters", "pip")
            os.makedirs(gdir)
            open(os.path.join(gdir, "reference.png"), "w").close()  # noqa: SIM115
            ex.write_json({"name": "Pip", "look": "Pip. ", "reference_image": "reference.png"},
                          os.path.join(gdir, "character.json"))
            [g] = ex.load_guests({"guests": ["pip"]}, root)
            self.assertEqual(g["reference_image"], os.path.join(gdir, "reference.png"))

    def test_should_have_no_guests_by_default(self):
        self.assertEqual(ex.load_guests({}, "/nonexistent"), [])


class WordsTest(unittest.TestCase):
    def test_should_treat_a_digit_and_its_word_as_the_same_word(self):
        # whisper writes "Number 6" for a correctly spoken "Number six"; that must not cost the take.
        self.assertEqual(ex.words("Number 6, and number 8"), ex.words("number six and number eight"))

    def test_should_treat_okay_and_ok_as_the_same_word(self):
        self.assertEqual(ex.words("Okay!"), ex.words("OK"))


class QcTest(unittest.TestCase):
    def test_should_score_an_exact_take_as_a_full_match(self):
        self.assertAlmostEqual(ex.line_match("Mars is red.", "mars is red"), 1.0)

    def test_should_score_the_wrong_words_low(self):
        self.assertLess(ex.line_match("Mars is red and dusty.", "Jupiter has a giant storm."), 0.3)

    def test_should_score_an_empty_transcript_as_zero(self):
        self.assertEqual(ex.line_match("Mars is red.", ""), 0.0)

    def test_should_hear_the_names_the_way_whisper_writes_them(self):
        self.assertEqual(ex.names_missing("Myra, Theo, hop in!", AUD), [])
        self.assertEqual(ex.names_missing("Meera! Teo!", AUD), [])

    def test_should_accept_every_heard_spelling_not_only_the_first(self):
        # Regression, 2026-09-26: three correct takes were rejected because one heard spelling was missing.
        self.assertEqual(ex.names_missing("See you soon, Myra. See you soon, Tio.", AUD), [])

    def test_should_not_hear_a_short_name_inside_a_longer_word(self):
        # A short name hides inside ordinary words ("Al" in "all", "also", "metal"): a substring match passes a
        # take that never said the name.
        al = {"name": "Al", "names": [{"spoken": "Al", "heard": ["al", "hal"]}]}
        self.assertEqual(ex.names_missing("We all built a metal robot, also a car!", al), ["Al"])
        self.assertEqual(ex.names_missing("And hello, Hal!", al), [])

    def test_should_name_the_missing_child(self):
        self.assertEqual(ex.names_missing("Myra, hop in!", AUD), ["Thee-oh"])

    def test_should_pass_a_good_bookend_take(self):
        ok, _ = ex.scene_verdict(GOOD["scenes"][0], "Myra! Theo! Hop in, we are flying past all 8 planets!", True, AUD)
        self.assertTrue(ok)

    def test_should_fail_a_bookend_take_that_mangles_a_name(self):
        ok, why = ex.scene_verdict(GOOD["scenes"][0], "Myra! Leo! Hop in, we are flying past all eight planets!", True, AUD)
        self.assertFalse(ok)
        self.assertIn("Thee-oh", why)

    def test_should_fail_a_take_that_says_something_else(self):
        ok, why = ex.scene_verdict(GOOD["scenes"][1], "Hello there, let us sing a song.", False, AUD)
        self.assertFalse(ok)
        self.assertIn("wrong words", why)


class ContactSheetTest(unittest.TestCase):
    def test_should_show_two_frames_per_scene_so_a_long_episode_is_not_undersampled(self):
        # 2026-09-26: a fixed 12-frame sheet showed only one frame per scene of a three-minute episode.
        self.assertEqual(ex.sheet_grid(12), (6, 4))
        self.assertEqual(ex.sheet_grid(6), (4, 3))

    def test_should_fit_every_frame_in_the_grid(self):
        for n in range(ex.MIN_SCENES, ex.MAX_SCENES + 1):
            cols, rows = ex.sheet_grid(n)
            self.assertGreaterEqual(cols * rows, 2 * n)


class CostTest(unittest.TestCase):
    def test_should_price_an_episode_by_seconds_rendered_at_the_model_rate(self):
        self.assertEqual(ex.estimate_credits(GOOD, CHAR), 5 * 15 * 30)

    def test_should_price_a_model_the_kit_does_not_know_at_the_highest_rate(self):
        # an unknown rate must over-estimate, never under-estimate: the number is used to decide whether to spend
        self.assertEqual(ex.estimate_credits(GOOD, dict(CHAR, model="future_model")), 5 * 15 * max(ex.CREDITS_PER_SECOND.values()))


class FinalProblemsTest(unittest.TestCase):
    def test_should_expect_three_minutes_from_twelve_scenes(self):
        long = dict(GOOD, scenes=[GOOD["scenes"][0], *[dict(GOOD["scenes"][1], id=f"m{i}") for i in range(10)], GOOD["scenes"][-1]])
        script = " ".join(s["line"] for s in long["scenes"]).replace("Mee-ra", "Myra").replace("Thee-oh", "Theo")
        self.assertEqual(ex.final_problems(long, script, seconds=181.0, lufs=-16.0, audience=AUD), [])
        self.assertTrue(ex.final_problems(long, script, seconds=90.0, lufs=-16.0, audience=AUD))

    def test_should_pass_a_finished_episode_that_says_its_script(self):
        self.assertEqual(ex.final_problems(GOOD, heard_script(), seconds=75.0, lufs=-16.1, audience=AUD), [])

    def test_should_fail_an_episode_that_is_the_wrong_length(self):
        found = ex.final_problems(GOOD, heard_script(), seconds=40.0, lufs=-16.0, audience=AUD)
        self.assertTrue(any("seconds" in p for p in found), found)

    def test_should_fail_an_episode_that_is_too_quiet(self):
        found = ex.final_problems(GOOD, heard_script(), seconds=75.0, lufs=-24.0, audience=AUD)
        self.assertTrue(any("LUFS" in p for p in found), found)

    def test_should_fail_an_episode_whose_mix_lost_the_dialogue(self):
        found = ex.final_problems(GOOD, "", seconds=75.0, lufs=-16.0, audience=AUD)
        self.assertTrue(any("script" in p for p in found), found)


class LoadCastTest(unittest.TestCase):
    def test_should_resolve_character_files_relative_to_the_character_folder(self):
        with tempfile.TemporaryDirectory() as root:
            cdir = os.path.join(root, "characters", "pip")
            os.makedirs(cdir)
            os.makedirs(os.path.join(root, "audiences"))
            os.makedirs(os.path.join(root, "music"))
            for f in ("ref.png", "voice.mp3"):
                open(os.path.join(cdir, f), "w").close()  # noqa: SIM115
            open(os.path.join(root, "music", "bed.mp3"), "w").close()
            ex.write_json({"name": "Pip", "pronoun": "It", "look": "Pip. ", "reference_image": "ref.png",
                           "voice_reference": "voice.mp3", "music": "bed.mp3"}, os.path.join(cdir, "character.json"))
            ex.write_json(AUD, os.path.join(root, "audiences", "kids.json"))
            ch, aud = ex.load_cast({"character": "pip", "audience": "kids"}, root)
            self.assertEqual(ch["reference_image"], os.path.join(cdir, "ref.png"))
            self.assertEqual(ch["music"], os.path.join(root, "music", "bed.mp3"))
            self.assertEqual(ch["model"], ex.DEFAULT_MODEL)
            self.assertEqual(aud["name"], "Mira and Theo")

    def test_should_say_which_file_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError) as cm:
                ex.load_cast({"character": "nobody", "audience": "kids"}, root)
            self.assertIn("nobody", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
