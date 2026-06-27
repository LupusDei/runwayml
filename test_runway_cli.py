"""Unit tests for the pure helpers in runway_cli.

Network and API calls are not exercised here — only the deterministic,
side-effect-free logic. Run with:  python3 -m unittest test_runway_cli
"""
import base64
import os
import tempfile
import unittest

import runway_cli as cli


class MimeForPathTests(unittest.TestCase):
    def test_known_extensions_map_to_content_types(self):
        self.assertEqual(cli.mime_for_path("a.png"), "image/png")
        self.assertEqual(cli.mime_for_path("a.JPG"), "image/jpeg")
        self.assertEqual(cli.mime_for_path("photo.jpeg"), "image/jpeg")
        self.assertEqual(cli.mime_for_path("x.webp"), "image/webp")

    def test_unsupported_extension_raises(self):
        with self.assertRaises(ValueError):
            cli.mime_for_path("animation.gif")


class BuildDataUriTests(unittest.TestCase):
    def test_data_uri_round_trips(self):
        raw = b"\x89PNG fake bytes"
        uri = cli.build_data_uri("logo.png", raw)
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        encoded = uri.split(",", 1)[1]
        self.assertEqual(base64.b64decode(encoded), raw)


class ResolveAssetTests(unittest.TestCase):
    def test_remote_uris_pass_through_untouched(self):
        for uri in (
            "https://x.com/a.jpg",
            "http://x.com/a.jpg",
            "data:image/png;base64,AAAA",
            "runway://abc",
        ):
            self.assertEqual(cli.resolve_asset(uri), uri)

    def test_local_file_becomes_data_uri(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"tiny")
            path = tmp.name
        try:
            uri = cli.resolve_asset(path)
            self.assertTrue(uri.startswith("data:image/png;base64,"))
        finally:
            os.unlink(path)

    def test_oversized_local_file_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"0" * (5 * 1024 * 1024 + 1))
            path = tmp.name
        try:
            with self.assertRaises(ValueError):
                cli.resolve_asset(path)
        finally:
            os.unlink(path)


class FirstOutputTests(unittest.TestCase):
    def test_reads_output_array(self):
        self.assertEqual(cli.first_output({"output": ["u1", "u2"]}), "u1")

    def test_falls_back_to_artifacts(self):
        self.assertEqual(cli.first_output({"artifacts": ["a1"]}), "a1")

    def test_none_when_empty(self):
        self.assertIsNone(cli.first_output({"output": []}))
        self.assertIsNone(cli.first_output({}))


class ParserTests(unittest.TestCase):
    def test_image_defaults(self):
        args = cli.build_parser().parse_args(["image", "a cat"])
        self.assertEqual(args.prompt, "a cat")
        self.assertEqual(args.model, "gen4_image")
        self.assertEqual(args.ratio, "1360:768")

    def test_video_parses_duration_as_int(self):
        args = cli.build_parser().parse_args(
            ["video", "x.jpg", "--duration", "10", "--model", "gen4_turbo"]
        )
        self.assertEqual(args.duration, 10)
        self.assertEqual(args.model, "gen4_turbo")
        self.assertEqual(args.image, "x.jpg")

    def test_upscale_defaults(self):
        args = cli.build_parser().parse_args(["upscale", "in.png", "-o", "out.png"])
        self.assertEqual(args.image, "in.png")
        self.assertEqual(args.model, "magnific_precision_upscaler_v2")
        self.assertEqual(args.out, "out.png")
        self.assertIs(args.func, cli.cmd_upscale)


if __name__ == "__main__":
    unittest.main()
