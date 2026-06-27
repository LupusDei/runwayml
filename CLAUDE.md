# Runway API Project

This repo is a toolkit + reference for building on the **Runway generative-media API**
(`docs.dev.runwayml.com`), funded by a **dev-program grant of $5,000 in API credits**.

> Full reference lives in **[`RUNWAY_API_INDEX.md`](./RUNWAY_API_INDEX.md)** — read it before
> answering API questions; don't rely on memory for models, params, pricing, or limits.

---

## Credits & account
- **Budget:** ~$5,000 ≈ **500,000 credits** (1 credit = $0.01).
- Spending the grant lands the org in **Tier 5** (20 concurrent generations).
- Roughly buys: ~28 hrs Gen4 Turbo video, ~11.6 hrs Gen4.5 video, or ~250k images.
- **Spend the API-org credits, not a consumer subscription** — always authenticate with the
  **dev-org API key** (`RUNWAYML_API_SECRET`), never the hosted OAuth connector, for grant work.
- Output URLs **expire after 24 hours** — download anything worth keeping (`-o` on the CLI).

## Setup (once)
```bash
export RUNWAYML_API_SECRET=key_xxx   # dev-org key; the SDKs, CLI, and MCP server all read this
```
Add it to your shell profile / a secret manager — never commit it.

---

## What's in this repo
| Path | What it is |
|---|---|
| `RUNWAY_API_INDEX.md` | Full functional + API reference (models, endpoints, pricing, limits, errors) |
| `runway-getting-started.html` | Single-page visual onboarding guide (open in a browser) |
| `runway_cli.py` | Dependency-free Python CLI over the REST API |
| `test_runway_cli.py` | Unit tests for the CLI's pure helpers |
| `.mcp.json` | Registers the local `runway` MCP server (reads `${RUNWAYML_API_SECRET}`) |
| `runway-api-mcp-server/` | Official MCP server, cloned & built (`build/index.js`) |
| `characters/` | One subfolder per character (see below) |

## Characters
Each character gets its own folder under `characters/<name>/`. Keep that structure when
adding new characters. Layout (see `characters/adjutant/` as the reference):
- Top level = the **deliverable package**: source image(s), `system_prompt.txt`,
  `knowledge_base*.txt`, motion test clip, `persona.md`, `CHARACTER_SETUP.md`.
- `exploration/` = the **generation history**: `icon_source.png`, early tests, and
  `variants/` + `finalists/` image rounds.
Character creation itself is a Runway **portal** step (no API); `CHARACTER_SETUP.md` in
each folder is the walkthrough.

## The CLI
```bash
./runway_cli.py image "a neon koi pond at dusk" -o koi.png
./runway_cli.py video ./start.jpg --model gen4_turbo --duration 5 -o clip.mp4
./runway_cli.py task <id>      # status / output URL
./runway_cli.py cancel <id>
./runway_cli.py org            # tier / credit info
```
- Submit → poll (≥5s) → print URL or download with `-o`.
- Defaults: image `gen4_image` @ `1360:768`; video `gen4.5` @ `1280:768`, 5s.
- Local images <5MB auto-encode to data URIs; host larger ones at an HTTPS URL.
- **Tests:** `python3 -m unittest test_runway_cli` (currently 11/11 passing).

## The MCP server
- Registered in `.mcp.json` as `runway`; restart Claude in this folder to load it.
- Uses the **local API-key server** so generations spend the **$5k grant**.
- Tools: `runway_generateVideo`, `runway_generateImage`, `runway_upscaleVideo`,
  `runway_editVideo`, `runway_getTask`, `runway_cancelTask`, `runway_getOrg`.
- Hosted alternative `https://mcp.runwayml.com/mcp` exists but **bills your subscription**, not the grant.

---

## Key facts worth remembering (gotchas)
- **Base URL** `https://api.dev.runwayml.com/v1/`; every request needs
  `Authorization: Bearer $RUNWAYML_API_SECRET` **and** `X-Runway-Version: 2024-11-06`.
- **Async task model:** `POST /v1/<endpoint>` → `{id}`; poll `GET /v1/tasks/{id}`;
  cancel `DELETE /v1/tasks/{id}`. Statuses: `PENDING → THROTTLED → RUNNING → SUCCEEDED|FAILED|CANCELED`.
- **No per-minute rate limit** — only a daily cap; over-concurrency just queues as `THROTTLED`.
- **`ratio` uses resolution strings** (`1280:768`, `768:1280`), **not** `16:9`/`9:16` (removed in this API version).
- **Start/end frames:** pass `promptImage` as `[{uri, position:"first"}, {uri, position:"last"}]`.
- **API keys are org-scoped, not user-scoped** — removing a teammate doesn't revoke their key.
- **Moderated/blocked generations still cost full credits**; repeated violations → suspension.
- Cheapest models for prototyping: video `gen4_turbo` (5 cr/s), image `gen4_image_turbo` (2 cr).
- **Name trap:** `mcp.runway.team` / `docs.runway.team` is a *different company* (mobile release
  management). The AI media tool is `runwayml.com` / `docs.dev.runwayml.com`.

## Conventions for working here
- Validate inputs (size, codec, ratio, Content-Type) before submitting; handle `429/502/503/504`
  with exponential backoff + jitter, and handle `FAILED` tasks.
- Keep new code covered by unit tests; keep functions under cyclomatic complexity 5.
- Prototype on the cheap models, switch to higher-quality ones only once prompts are dialed in.
</content>
