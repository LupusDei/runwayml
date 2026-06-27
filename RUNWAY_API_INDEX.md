# Runway API — Functional & Developer Index

> A complete reference for the Runway Developer Platform (`docs.dev.runwayml.com`).
> Built for the $5k token dev-program credit. Last compiled: **2026-06-25**.
> API version in use: **`2024-11-06`**.

---

## 1. What Runway's API Is

Runway exposes its generative media models over a REST API so you can embed
text→image, image/text→video, video→video editing, image upscaling, text→audio,
and real-time conversational avatars ("Characters") into your own apps.

Two distinct product families:

| Family | What it does | Nature |
|---|---|---|
| **Generation API** | Create images, video, audio, upscales | Async, task-based (submit → poll → fetch output) |
| **Characters (GWM-1)** | Interactive conversational AI avatars | Real-time, streaming, tool-calling, video meetings |

---

## 2. Core Concepts

### 2.1 Base URL & Auth
- **Base URL:** `https://api.dev.runwayml.com/v1/`
- **Headers (every request):**
  - `Authorization: Bearer $RUNWAYML_API_SECRET`
  - `X-Runway-Version: 2024-11-06`
- **Env var convention:** `RUNWAYML_API_SECRET` (SDKs read this automatically).

### 2.2 Organizations & Keys
- An **organization** = your integration. It owns API keys, billing/credits, config.
- Keys are **org-scoped, not user-scoped** → removing a user does **not** revoke their key. Disable keys manually.
- Keys are shown **once** at creation — save immediately to a secret manager.
- Best practice: separate keys per environment (staging/prod) and per developer.

### 2.3 The Async Task Model
All generation is asynchronous:
1. **Submit** — `POST /v1/<endpoint>` → returns `{ "id": "task_xxx" }`
2. **Poll** — `GET /v1/tasks/{id}` → returns the task with a `status`
3. **Fetch** — when `SUCCEEDED`, output URLs are in the task's output/artifacts array
4. **Cancel** — `DELETE /v1/tasks/{id}`

**Task statuses:** `PENDING` → `THROTTLED` → `RUNNING` → `SUCCEEDED` | `FAILED` | `CANCELED`
- `THROTTLED` = accepted & stored but not yet enqueued (you hit your concurrency cap; it queues in submission order automatically — no client-side rate limiting needed).
- **Polling guidance:** interval **≥ 5 seconds**, add jitter, exponential backoff on non-200s.
- SDKs abstract this with `.waitForTaskOutput()` (Node) / `.wait_for_task_output()` (Python).

---

## 3. Models Catalog

### 3.1 Video generation
| Model ID | Inputs | Notes |
|---|---|---|
| `seedance2` | text / image / video | Flagship; up to 4K |
| `seedance2_fast` | text / image / video | Faster/cheaper, 480p/720p |
| `aleph2` | video + text/image edits | Video-to-video editing (NEW) |
| `gen4.5` | text / image | Strong general image-to-video |
| `gen4_turbo` | image | Cheapest video (5 cr/s) |
| `gen4_aleph` | video + text/image | **Deprecated — sunset 2026-07-30** |
| `act_two` | image / video | Performance/character motion transfer |
| `veo3` | text / image | Google Veo 3 |
| `veo3.1` | text / image | Audio optional |
| `veo3.1_fast` | text / image | Faster Veo, audio optional |
| `happyhorse_1_0` | text / image | 720p/1080p |

### 3.2 Real-time avatars
| Model ID | I/O | Notes |
|---|---|---|
| `gwm1_avatars` | conversational text → video + audio | Powers Characters |

### 3.3 Image generation
| Model ID | Notes |
|---|---|
| `gen4_image` | 720p / 1080p |
| `gen4_image_turbo` | cheapest (2 cr) |
| `gemini_image3_pro` | Google, up to 4K |
| `gpt_image_2` | OpenAI GPT Image 2 |
| `gemini_2.5_flash` | fast/cheap |

### 3.4 Image upscale
| Model ID | Notes |
|---|---|
| `magnific_precision_upscaler_v2` | precision upscaler |

### 3.5 Audio (ElevenLabs-backed)
| Model ID | Function |
|---|---|
| `eleven_multilingual_v2` | Text-to-speech |
| `eleven_text_to_sound_v2` | Text-to-sound-effects |
| `eleven_voice_isolation` | Audio cleanup |
| `eleven_voice_dubbing` | Dubbing |
| `eleven_multilingual_sts_v2` | Speech-to-speech |

---

## 4. Endpoints

| Operation | Method & Path | Node SDK | Python SDK |
|---|---|---|---|
| Text → image | `POST /v1/text_to_image` | `client.textToImage.create` | `client.text_to_image.create` |
| Image/Text → video | `POST /v1/image_to_video` | `client.imageToVideo.create` | `client.image_to_video.create` |
| Video → video | `POST /v1/video_to_video` | — | — |
| Character performance | `POST /v1/character_performance` | `client.characterPerformance.create` | `client.character_performance.create` |
| Image upscale | `POST /v1/image_upscale` | — | — |
| Video upscale | `POST /v1/video_upscale` | — | — |
| Audio (TTS etc.) | model-specific endpoints | — | — |
| Get task | `GET /v1/tasks/{id}` | `client.tasks.retrieve` | `client.tasks.retrieve` |
| Cancel/delete task | `DELETE /v1/tasks/{id}` | — | — |
| Ephemeral upload | `POST /v1/uploads` | `client.uploads.createEphemeral` | `client.uploads.create_ephemeral` |

### 4.1 Key parameters (`image_to_video`, API `2024-11-06`)
- `model` — e.g. `gen4.5`, `gen4_turbo`, `veo3.1`, `seedance2` (required)
- `promptImage` — either a string URI **or** an array of `{ uri, position }` where `position` ∈ `"first"|"last"` (lets you set start AND end frames). Each position must be unique.
- `promptText` — guidance text (optional)
- `ratio` — direct resolution string (the old `16:9`/`9:16` are **no longer accepted**). ⚠️ **The valid set is per-model** — don't trust a single example. gen4_turbo image→video accepts `1280:720 720:1280 1104:832 832:1104 960:960 1584:672`; other models differ. Send a wrong value and the 400 response lists the valid options.
- `duration` — seconds (model-dependent)
- `seed` — `0`–`4294967295`
- `contentModeration` — object to relax public-figure strictness (see §8)

### 4.2 Key parameters (`text_to_image`)
- `model` — e.g. `gen4_image` (required)
- `promptText` — required
- `ratio` — e.g. `1360:768`, `1920:1080` (model-dependent)
- reference images + `seed` optional

### 4.3 Key parameters (`image_upscale`) — verified by schema probe
- `model` — `magnific_precision_upscaler_v2` (required)
- `imageUri` — URL, data URI, or `runway://` URI of the image (required)
- Returns the standard task object; output is the upscaled image URL. ~25 cr (150 if >4096px).
- Probe technique: `POST` with `{}` then `{ "model": "..." }` and read the 400 `issues[]` to
  reveal required fields — how this schema was discovered.

---

## 5. Assets — Inputs, Uploads, Outputs

### 5.1 Three ways to pass an asset
1. **HTTPS URL** — must use HTTPS + domain (no IPs), valid `Content-Type` & `Content-Length`, no redirects (3XX fails), ≤2048 chars, support HEAD requests. Runway's fetcher User-Agent starts with `RunwayML API/`.
2. **Base64 data URI** — `data:<content-type>;base64,...` (note: encoding adds ~33%).
3. **Ephemeral upload** — `runway://...` URI, valid **24h**, reusable.

### 5.2 Size limits
| Type | URL | Data URI | Ephemeral upload |
|---|---|---|---|
| Image | 16 MB | 5 MB | 200 MB |
| Video | 32 MB | 16 MB | 200 MB |
| Audio | 32 MB | 16 MB | 200 MB |

Ephemeral min size 512 bytes; requires credits on the org.

### 5.3 Accepted formats
- **Image:** JPEG (`image/jpg`/`image/jpeg`), PNG (`image/png`), WebP (`image/webp`). **GIF not supported.**
- **Video:** MP4 (H.264/H.265/AV1), MOV (H.264/H.265/ProRes), MKV, WebM, 3GP, OGV. AVI/MPEG/FLV legacy/discouraged.
- **Audio:** MP3, WAV (PCM), FLAC, M4A (AAC/ALAC), AAC.
- `application/octet-stream` and generic content types are **rejected**. Content-Type header (not file extension) decides validity.

### 5.4 Aspect-ratio constraints (input)
- Gen-4.5 image-to-video: **0.5–2.0**
- HappyHorse 1.0: **0.55–1.8**
- Gemini 2.5 Flash: **0.25–4.0**
- Reference images outside 640×640–4K are resized; auto-crop applies when input ratio ≠ output ratio.

### 5.5 Ephemeral upload flow (REST)
```
POST /v1/uploads { "filename": "video.mp4", "type": "ephemeral" }
→ { uploadUrl, fields, runwayUri }
POST file (multipart) to uploadUrl with all fields → use runwayUri in generation requests
```

---

## 6. Pricing (1 credit = $0.01)

### Video (credits/second unless noted)
| Model | Cost |
|---|---|
| Seedance2 | 36 (480/720p), 40 (1080p), 150 (4K) |
| Seedance2 Fast | 29 (480/720p) |
| Aleph2 | 28 (56-credit minimum) |
| Gen4.5 | 12 |
| Gen4 Turbo | 5 |
| Veo3 | 40 |
| Veo3.1 | 40 (with audio) / 20 (no audio) |
| Veo3.1 Fast | 15 (audio) / 10 (no audio) |
| HappyHorse 1.0 | 15 (720p) / 30 (1080p) |
| Act Two | 5 |

### Image (credits each)
| Model | Cost |
|---|---|
| Gen4 Image | 5 (720p) / 8 (1080p) |
| Gen4 Image Turbo | 2 |
| Gemini Image3 Pro | 20 (1K/2K) / 40 (4K) |
| GPT Image 2 | 1–41 (by quality/res) |
| Gemini 2.5 Flash | 5 |

### Other
- Magnific upscaler: 25 (standard) / 150 (>4096px)
- Eleven Multilingual V2 TTS: 1 cr / 50 chars
- Eleven Voice Dubbing: 1 cr / 2 sec
- GWM1 Avatars (real-time): 2 cr upfront + 2 cr / 6 sec

### What $5,000 buys (≈500,000 credits)
| At... | You get roughly |
|---|---|
| Gen4 Turbo (5 cr/s) | ~100,000 s ≈ **27.8 hrs** of video |
| Gen4.5 (12 cr/s) | ~41,600 s ≈ **11.6 hrs** of video |
| Veo3.1 no-audio (20 cr/s) | ~25,000 s ≈ **6.9 hrs** of video |
| Gen4 Image Turbo (2 cr) | ~250,000 images |
| Gen4 Image (5 cr) | ~100,000 images |

---

## 7. Usage Tiers, Rate Limits & Billing

- **No per-minute request limit** — only the daily generation cap matters.
- **Concurrency** governs how many tasks run at once; excess → `THROTTLED` queue.
- Daily caps use a **24-hour rolling window**. Tier upgrades are **immediate** on hitting spend thresholds.

| Tier | Concurrency | Daily max | Monthly spend cap | Reached after |
|---|---|---|---|---|
| 1 | 1–2 | 50–200 | $100 | start |
| 2 | 3 | 500–1,000 | $500 | $50 spent |
| 3 | 5 | 1,000–2,000 | $2,000 | $100 spent |
| 4 | 10 | 5,000–10,000 | $20,000 | $1,000 spent |
| 5 | 20 | 25,000–30,000 | $100,000 | $5,000 spent |

> With $5k of credits you'll naturally land in **Tier 5** (20 concurrent). Custom/guaranteed concurrency available via exception form.

- **Autobilling:** set a payment method + recharge threshold so credits don't run dry mid-run.
- Minimum initial credit purchase: **$10**.

---

## 8. Content Moderation
- Both **text and image** inputs are evaluated.
- Default moderation is `auto`; by default it **blocks recognizable public figures**. Add a `contentModeration` object to a request to be less strict about public figures.
- **Moderated generations still cost full credits** (no refund).
- Repeated violations → **account suspension** (appealable from your portal email).
- Moderation rejections surface as `status: FAILED` with `failure` / `failureCode` fields.

---

## 9. Error Handling
| Code | Meaning | Retry? |
|---|---|---|
| 400 | Bad input (JSON details) | No |
| 401 | Invalid API key | No |
| 404 | Resource not found | No |
| 405 | Wrong HTTP method | No |
| 429 | Rate limited | Yes |
| 502 / 503 | Runway shedding load | Yes |
| 504 | Runway overloaded | Yes |

Retry retryable errors with exponential backoff + up to 50% jitter. SDKs auto-retry.
Task-level failures: poll returns `FAILED` with `failure`/`failureCode`; SDKs raise `TaskFailedError` (Node) / exception with `taskDetails`.

---

## 10. Characters (GWM-1 conversational avatars)
Interactive, real-time digital personas from a single image (photoreal or animated).
Capabilities:
- **Voice:** design from a text prompt or clone from an audio sample; custom voices.
- **Real-time video meetings:** camera + screen sharing.
- **Tool calling:** client-side & server-side tools to take actions / hit external systems.
- **Knowledge base:** ground responses in your documents.
- **LiveKit Agents** integration; embeddable **widget**.
- No fine-tuning required.

Use cases: branded customer support, tutoring, brand mascots, interactive gaming.
Docs tree: `/characters/{quickstart,concepts,integration,widget,documents,custom-voice,tools,video-meeting,screens,livekit,troubleshooting}`.

---

## 11. Recipes (production-ready workflows)
Prebuilt pipelines bundling model choice + prompting + post-processing:
1. **Product Ad** — product photo → polished ad video
2. **Product Swap** — replace product in a reference video
3. **Product UGC** — influencer-style UGC with your product
4. **Multi-Shot Video** — multi-scene/cut storytelling
5. **Marketing Stock Image** — brand-aligned stock imagery
6. **Product Campaign Image** — ad-style campaign visuals

See also `/recipes/reference-media/` for input media guidelines.

---

## 12. SDKs & Tooling
- **Node.js:** `npm install @runwayml/sdk` (Node 18+, TypeScript types). `new RunwayML()` reads `RUNWAYML_API_SECRET`.
- **Python:** `pip install runwayml` (Python 3.8+, MyPy-typed).
- **cURL / raw HTTP:** fully supported with the two required headers.
- **GitHub:** `github.com/runwayml/skills` (Claude Code skills + examples).
- **Playground / model reference:** `dev.runwayml.com/models`.

### 12.1 MCP server
Two official options:
- **Hosted (OAuth):** add `https://mcp.runwayml.com/mcp` as a custom connector in Claude/Cursor/ChatGPT, sign in with your Runway account. No API key. **Bills your subscription plan**, not the API-org credits.
- **Local (API key):** `github.com/runwayml/runway-api-mcp-server` — runs over stdio (`node build/index.js`), authed via `RUNWAYML_API_SECRET`, so it **spends the $5k API credits**. ✅ recommended for the grant.
  - Cloned & built in this repo at `./runway-api-mcp-server/`; registered in `./.mcp.json` as the `runway` server (reads `RUNWAYML_API_SECRET` from env).
  - Tools: `runway_generateVideo`, `runway_generateImage`, `runway_upscaleVideo`, `runway_editVideo`, `runway_getTask`, `runway_cancelTask`, `runway_getOrg`.
  - For Claude Desktop, copy the block into `~/Library/Application Support/Claude/claude_desktop_config.json` (absolute path + literal key) and restart.

> Note: there is **no** official standalone CLI. The SDKs are libraries. `mcp.runway.team` is a *different company* (mobile release management) — ignore it.

### 12.2 Local `runway` CLI (in this repo)
A dependency-free Python CLI (`runway_cli.py`) over the REST API — submit, poll (≥5s), print/download:
```bash
export RUNWAYML_API_SECRET=key_xxx
./runway_cli.py image "a neon koi pond at dusk" -o koi.png
./runway_cli.py video ./start.jpg --model gen4_turbo --duration 5 -o clip.mp4
./runway_cli.py task <id>     # status / output URL
./runway_cli.py cancel <id>
./runway_cli.py org           # tier / credits
```
Tests: `python3 -m unittest test_runway_cli`. Output URLs expire after 24h — use `-o`.

### Minimal examples
**Node (text→image):**
```js
import RunwayML from '@runwayml/sdk';
const client = new RunwayML();
const task = await client.textToImage.create({
  model: 'gen4_image',
  promptText: 'A beautiful sunset over a calm ocean',
  ratio: '1360:768',
}).waitForTaskOutput();
console.log(task.output[0]);
```

**Python (image→video):**
```python
from runwayml import RunwayML
client = RunwayML()
task = client.image_to_video.create(
    model='gen4.5',
    prompt_image='https://example.com/start.jpg',
    prompt_text='slow cinematic dolly in',
    ratio='1280:768',
    duration=5,
).wait_for_task_output()
print(task.output[0])
```

**cURL (submit + poll):**
```bash
curl -s https://api.dev.runwayml.com/v1/image_to_video \
  -H "Authorization: Bearer $RUNWAYML_API_SECRET" \
  -H "X-Runway-Version: 2024-11-06" \
  -H "Content-Type: application/json" \
  -d '{"model":"gen4_turbo","promptImage":"https://.../img.jpg","ratio":"1280:768","duration":5}'
# → {"id":"task_..."}  then:
curl -s https://api.dev.runwayml.com/v1/tasks/<id> \
  -H "Authorization: Bearer $RUNWAYML_API_SECRET" \
  -H "X-Runway-Version: 2024-11-06"
```

---

## 13. Go-Live Checklist
- [ ] Tier-up to expected daily volume; verify concurrency headroom.
- [ ] Enable **autobilling** (method + recharge threshold) so credits don't deplete.
- [ ] Keys: per-env + per-dev, in a secret manager; `git grep "key_"` to confirm none committed; disable shared/unused keys.
- [ ] Handle `429`/`502`/`503`/`504` with backoff + jitter; handle `FAILED` tasks.
- [ ] Validate inputs (size, codec, ratio, Content-Type) before submitting.
- [ ] Confirm a monitored email for billing/suspension alerts (not spam-filtered).
- [ ] Ensure use case fits content policy; add client-side moderation if needed.
- [ ] Monitor error rate, daily volume, credit burn, throttling.

---

## 14. Source Map (docs paths)
- Get started: `/guides/{setup,using-the-api,models,pricing,go-live}/`
- API details: `/api-details/{sdks,moderation,versioning,api_changelog,versions/2024-11-06}/`
- Assets: `/assets/{inputs,uploads,outputs}/`
- Usage/billing: `/usage/{autobilling,tiers,attribution,organizations-and-roles}/`
- Errors: `/errors/{errors,task-failures,troubleshooting}/`
- Characters: `/characters/...`  •  Recipes: `/recipes/...`
- Portal: `https://dev.runwayml.com/`  •  Docs: `https://docs.dev.runwayml.com/`
</content>
</invoke>
