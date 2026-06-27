#!/usr/bin/env python3
"""Minimal, dependency-free CLI for the Runway generation API.

Uses only the Python standard library, so there is nothing to install.
It talks to the REST API directly: submit a task, poll until done, then
print (or download) the resulting media URL.

Auth: set RUNWAYML_API_SECRET in your environment (your dev-org API key,
so generations draw down the $5k API credits).

Examples:
    export RUNWAYML_API_SECRET=key_xxx
    ./runway_cli.py image "a neon koi pond at dusk" -o koi.png
    ./runway_cli.py video https://example.com/start.jpg --prompt "slow dolly in" -o clip.mp4
    ./runway_cli.py video ./start.jpg --model gen4_turbo --duration 5
    ./runway_cli.py task task_abc123
    ./runway_cli.py cancel task_abc123
    ./runway_cli.py org
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"
POLL_INTERVAL_SECONDS = 5
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELED", "CANCELLED"}

# content-type lookup for turning a local file into a data URI
IMAGE_MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def mime_for_path(path: str) -> str:
    """Return the Runway-accepted image content-type for a file path."""
    _, ext = os.path.splitext(path.lower())
    if ext not in IMAGE_MIME_BY_EXT:
        raise ValueError(f"Unsupported image type '{ext}'. Use JPEG, PNG or WebP.")
    return IMAGE_MIME_BY_EXT[ext]


def build_data_uri(path: str, raw: bytes) -> str:
    """Build a base64 data URI for a local image's bytes."""
    mime = mime_for_path(path)
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def resolve_asset(arg: str) -> str:
    """Resolve a user-supplied asset into a URI the API accepts.

    Passes through http(s)/data/runway URIs untouched; reads a local file
    into a base64 data URI otherwise.
    """
    if arg.startswith(("http://", "https://", "data:", "runway://")):
        return arg
    with open(arg, "rb") as handle:
        raw = handle.read()
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError(
            "Local image exceeds the 5MB data-URI limit. "
            "Host it at an HTTPS URL and pass that instead."
        )
    return build_data_uri(arg, raw)


def auth_headers() -> dict:
    """Build the required request headers, or exit if the key is missing."""
    secret = os.environ.get("RUNWAYML_API_SECRET")
    if not secret:
        sys.exit("RUNWAYML_API_SECRET is not set. Export your Runway API key first.")
    return {
        "Authorization": f"Bearer {secret}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def request(method: str, path: str, body: dict | None = None) -> dict:
    """Make one JSON API call and return the parsed response."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=data, headers=auth_headers(), method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")
        sys.exit(f"API error {err.code}: {detail}")


def first_output(task: dict) -> str | None:
    """Return the first output URL from a finished task, if present."""
    output = task.get("output") or task.get("artifacts") or []
    return output[0] if output else None


def poll_task(task_id: str) -> dict:
    """Poll a task until it reaches a terminal status, printing progress."""
    while True:
        task = request("GET", f"/tasks/{task_id}")
        status = task.get("status", "UNKNOWN")
        if status in TERMINAL_STATUSES:
            return task
        print(f"  …{status}", file=sys.stderr)
        time.sleep(POLL_INTERVAL_SECONDS)


def deliver(task: dict, out_path: str | None) -> None:
    """Report a finished task: download to out_path or print its URL."""
    if task.get("status") not in ("SUCCEEDED",):
        sys.exit(f"Task did not succeed: {json.dumps(task, indent=2)}")
    url = first_output(task)
    if not url:
        sys.exit(f"Task succeeded but had no output: {json.dumps(task, indent=2)}")
    if not out_path:
        print(url)
        return
    urllib.request.urlretrieve(url, out_path)
    print(f"Saved {out_path}")


def run_and_deliver(path: str, body: dict, out_path: str | None) -> None:
    """Submit a generation task, poll it, and deliver the result."""
    created = request("POST", path, body)
    task_id = created["id"]
    print(f"Task {task_id} submitted.", file=sys.stderr)
    deliver(poll_task(task_id), out_path)


def cmd_image(args: argparse.Namespace) -> None:
    body = {"model": args.model, "promptText": args.prompt, "ratio": args.ratio}
    if args.reference:
        body["referenceImages"] = [{"uri": resolve_asset(r)} for r in args.reference]
    run_and_deliver("/text_to_image", body, args.out)


def cmd_video(args: argparse.Namespace) -> None:
    body = {
        "model": args.model,
        "promptImage": resolve_asset(args.image),
        "ratio": args.ratio,
        "duration": args.duration,
    }
    if args.prompt:
        body["promptText"] = args.prompt
    run_and_deliver("/image_to_video", body, args.out)


def cmd_upscale(args: argparse.Namespace) -> None:
    body = {"model": args.model, "imageUri": resolve_asset(args.image)}
    run_and_deliver("/image_upscale", body, args.out)


def cmd_task(args: argparse.Namespace) -> None:
    print(json.dumps(request("GET", f"/tasks/{args.id}"), indent=2))


def cmd_cancel(args: argparse.Namespace) -> None:
    request("DELETE", f"/tasks/{args.id}")
    print(f"Canceled {args.id}")


def cmd_org(_: argparse.Namespace) -> None:
    print(json.dumps(request("GET", "/organization"), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runway", description="Runway API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    img = sub.add_parser("image", help="text -> image")
    img.add_argument("prompt")
    img.add_argument("--model", default="gen4_image")
    img.add_argument("--ratio", default="1360:768")
    img.add_argument("--reference", action="append", help="reference image URL/path")
    img.add_argument("-o", "--out", help="download to this file")
    img.set_defaults(func=cmd_image)

    vid = sub.add_parser("video", help="image -> video")
    vid.add_argument("image", help="prompt image: URL, data URI, or local file")
    vid.add_argument("--prompt", help="optional text guidance")
    vid.add_argument("--model", default="gen4.5")
    vid.add_argument("--ratio", default="1280:768")
    vid.add_argument("--duration", type=int, default=5)
    vid.add_argument("-o", "--out", help="download to this file")
    vid.set_defaults(func=cmd_video)

    ups = sub.add_parser("upscale", help="upscale an image")
    ups.add_argument("image", help="image to upscale: URL, data URI, or local file")
    ups.add_argument("--model", default="magnific_precision_upscaler_v2")
    ups.add_argument("-o", "--out", help="download to this file")
    ups.set_defaults(func=cmd_upscale)

    task = sub.add_parser("task", help="get task status")
    task.add_argument("id")
    task.set_defaults(func=cmd_task)

    cancel = sub.add_parser("cancel", help="cancel/delete a task")
    cancel.add_argument("id")
    cancel.set_defaults(func=cmd_cancel)

    org = sub.add_parser("org", help="organization info")
    org.set_defaults(func=cmd_org)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
