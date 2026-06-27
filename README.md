# runwayml

A working toolkit and reference for building on the **Runway generative-media API**
(`docs.dev.runwayml.com`) — a dependency-free CLI, the local MCP server, full API docs,
and a growing set of conversational **characters**.

> **For agents/Claude:** read [`CLAUDE.md`](./CLAUDE.md) first — it has the project map,
> credit rules, gotchas, and hard-won lessons. Full API reference is in
> [`RUNWAY_API_INDEX.md`](./RUNWAY_API_INDEX.md).

## Quick start
```bash
cp .env.example .env          # paste your Runway dev-org API key
set -a && . ./.env && set +a  # load it into the shell

./runway_cli.py image "a neon koi pond at dusk" -o koi.png
./runway_cli.py video ./start.jpg --model gen4_turbo --ratio 1280:720 --duration 5 -o clip.mp4
./runway_cli.py upscale ./koi.png -o koi_4k.png
./runway_cli.py org           # tier / credit info
```
The CLI is pure Python standard library — nothing to install. Run the tests with
`python3 -m unittest test_runway_cli`.

## What's here
| Path | What it is |
|---|---|
| `runway_cli.py` / `test_runway_cli.py` | Dependency-free CLI over the REST API, + unit tests |
| `RUNWAY_API_INDEX.md` | Full API reference: models, endpoints, pricing, limits, errors |
| `runway-getting-started.html` | Single-page visual onboarding guide (open in a browser) |
| `.mcp.json` | Registers the local `runway` MCP server (reads `${RUNWAYML_API_SECRET}`) |
| `runway-api-mcp-server/` | The local API-key MCP server (run `npm install` here after cloning) |
| `characters/` | One folder per character — see below |
| `CLAUDE.md` | Project guide, conventions, and lessons learned |

## MCP server
The `runway` server in `.mcp.json` uses the **local API-key** server so generations spend
your API credits (not a consumer subscription). After cloning this repo:
```bash
cd runway-api-mcp-server && npm install   # node_modules/ is gitignored; build/ is committed
```
Then restart your MCP client in this folder.

## Characters
Each character lives in `characters/<name>/`:
- **Top level** = the deliverable package: source image(s), `system_prompt.txt`,
  `knowledge_base*.txt`, `persona.md`, `CHARACTER_SETUP.md`, and a motion test clip.
- **`exploration/`** = generation history (image variants, early tests, voice samples).

Current characters: **adjutant** (a synthetic aide-de-camp AI) and **todd** (a real-person
avatar of a 6lock co-founder, with a cloned-voice sample). Character *creation* is a Runway
**portal** step — each folder's `CHARACTER_SETUP.md` is the walkthrough.

## Notes
- **Secrets:** `.env` is gitignored — never commit your key. `.env.example` shows the format.
- **Media:** `*.mp4` / `*.mp3` are gitignored to keep the repo lean; regenerate clips with the
  CLI, or re-pull voice samples per `characters/<name>/CHARACTER_SETUP.md`.
- **Output URLs from Runway expire after 24h** — always download with `-o`.
</content>
