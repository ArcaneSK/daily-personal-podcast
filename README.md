# Daily Personal Podcast

A personal daily podcast generator. You write what you want to hear about as
plain-English markdown segments; a Claude-driven pipeline researches each
segment with live web search, scripts a two-host conversation, synthesizes
the audio with ElevenLabs (or any TTS provider you plug in), and publishes
a static, double-clickable site you can listen to from `file://` — no server
required.

It is built for a single listener: **you**. The point isn't a polished show
for an audience, it's a daily briefing that's actually about your interests,
your portfolio, your taste, your priorities. Yours. Locally generated, with
your own credentials, on your own machine.

## What it sounds like

Each episode is structured as a two-host conversation between a "driver"
who asks the obvious questions and an "info-bringer" who delivers the
substance. The flow is:

1. **Cold open** — the info-bringer teases the day's most striking item.
2. **Body segments** — one per topic you author (AI news, markets,
   government, whatever you want).
3. **What you should know today** — a rapid-fire mini-segment of one-line
   blurbs for stories that didn't merit a full segment.
4. **Outro** — clean sign-off with a forward look.

Optional ElevenLabs-generated stingers play between segments.

## Features

- **Topic segments are just markdown.** Free-form prose; no schema to
  learn. You describe what you want covered and the agent figures out how.
- **Live web research per segment.** Each segment runs its own
  Claude Agent SDK research call with web search and fetch tools, then
  classifies its result as `full` / `blurb` / `empty`. Empty segments
  drop; one-story "blurb" segments roll into the rapid-fire mini segment;
  full segments get their own conversation.
- **Two-host scripting.** A single Claude call composes the whole
  show — cold open through outro — with explicit anti-padding rules so
  it stays tight.
- **Pluggable TTS.** ElevenLabs by default (great voices, voice cloning
  if you want it); built-in OpenAI, Edge (free), and a fake provider for
  tests. Drop in your own provider as `app.tts.mine.MyProvider`.
- **Optional SFX / music stingers.** A 3-second cold-open sting, a
  ~1-second segue, and a 2-second outro tail, all generated via the
  ElevenLabs sound-generation API and cached forever.
- **Static, double-clickable site.** A single-page accordion of all
  episodes with client-side search and pagination. `public/index.html`
  works via `file://`, no web server.
- **Token-bounded continuity.** A rolling 7-day digest plus per-segment
  history files keep the agent aware of recurring threads without ever
  growing unbounded.
- **RSS feed** ready for any podcast app.
- **Idempotent CLI.** Each phase (`prepare` / `research` / `script` /
  `synthesize` / `publish`) writes to disk before the next one reads, so
  you can resume from any failure without redoing earlier work.

## Quick start

You'll need:

- [**uv**](https://github.com/astral-sh/uv) (Python package + venv manager)
- **Python 3.11+** (uv installs one if you don't have it)
- **ffmpeg** on `PATH` (audio stitching)
- An **ElevenLabs API key** (for the default TTS; free tier works to start)
- **Claude credentials.** The pipeline uses `claude-agent-sdk`, which
  auto-detects your local Claude Code session — including a Claude Max
  subscription. **Do NOT set `ANTHROPIC_API_KEY`** unless you specifically
  want to bill the API account; if it's set, the SDK may prefer it over
  your Max session.

Then:

```bash
git clone <this-repo> daily-personal-podcast
cd daily-personal-podcast

# 1. Install deps
uv venv
uv pip install -e ".[dev]"

# 2. Configure
cp config.example.yaml config.yaml
# edit config.yaml: set host names, ElevenLabs voice IDs, base_url

echo "ELEVENLABS_API_KEY=sk_your_key_here" > .env

# 3. Author at least one segment
cp segments/_example-01-intro.md segments/01-intro.md
cp segments/_example-02-tech-news.md segments/02-tech-news.md
cp segments/_example-99-outro.md segments/99-outro.md
# edit any of those to match what you actually want covered

# 4. Generate today's episode
uv run python -m app generate
```

Open `public/index.html` in any browser to hear the result.

## Authoring segments

A segment is a markdown file at `segments/NN-name.md`:

- The **two-digit prefix** sets order. `01-intro.md` runs first, `99-outro.md`
  runs last. Anything in between is a body segment in lexical order.
- A **leading underscore** disables the segment. `_TEMPLATE.md` and the
  `_example-*.md` files are skipped automatically.
- The **file body is free-form prose.** Describe what you want covered,
  what to skip, what tone you want, what sources to prefer, what
  recurring threads matter to you. The research agent reads it
  verbatim as instructions.

Two slots are positional and always preserved in the rundown, regardless
of whether their research call returned anything:

- **Intro (`01-*`):** the cold open and show open.
- **Outro (`99-*`):** the show closer.

These are typically narrator-driven shells with no research — their prose
should say "skip research" so they don't waste a research call.

See `segments/_TEMPLATE.md` for the canonical structure and the
`segments/_example-*.md` files for filled-in working examples.

## Scheduling

The pipeline is designed to be triggered on a schedule by Claude Code (or
any agent that can read `GENERATE.md` and run a shell command). The
`GENERATE.md` file in the repo root is the entire instruction set Claude
needs:

```
You are generating today's episode. Read GENERATE.md, run the steps,
commit the output.
```

Set up a Claude Code scheduled task pointing at this directory. There's no
machine-specific cron, no `systemd` unit; the instruction doc is portable
to any scaffold that runs Claude.

For one-off runs, just `uv run python -m app generate` from the repo.

## Customization

### TTS provider

Default is ElevenLabs. Switch to OpenAI, free Edge TTS, or your own:

```yaml
# config.yaml
tts:
  provider: openai          # built-in: elevenlabs | openai | edge | fake
  # or a fully-qualified module path:
  # provider: my_pkg.MyProvider
```

To bring your own provider, drop a class implementing the protocol from
`app/tts/base.py` (two methods: `synthesize(text, voice_id)` and
`voice_for_role(role)`). See `app/tts/custom.py.example` for the stub.

### Voices

Get your ElevenLabs voice IDs from
[elevenlabs.io/app/voices](https://elevenlabs.io/app/voices) or the
`/v1/voices` API and paste them into `config.yaml: tts.voices`. The
`narrator` slot should mirror `host_a` for backward compatibility.

### Show structure & tone

Each segment's prose is the strongest lever — that's where you describe
the tone, sources, and topics. The two-host roles (driver vs. info-bringer)
are defined in `config.yaml: show.host_a` / `show.host_b` personas. The
script-writer's hard rules (cold open, anti-padding, lead-with-the-point)
are in `app/script.py:_SYSTEM_PROMPT`; tweak there if you want a
different show shape.

### SFX / music stingers

Three cues are generated once via the ElevenLabs sound-generation API
and cached at `assets/sfx/` (gitignored). Tweak the prompts in
`config.yaml: sfx`, or set `sfx.enabled: false` to skip entirely.

## Architecture in one diagram

```
                    GENERATE.md  <—— Claude reads this on schedule
                         │
                         ▼
                  python -m app generate
                         │
   ┌─────────────────────┼─────────────────────────────────┐
   ▼                     ▼                                 ▼
PREPARE              RESEARCH (parallel)              SCRIPT (one Claude call)
discover            Claude Agent SDK +              two-host transcript with
segments,           web_search + web_fetch,         status-aware filtering
write manifest      classify full/blurb/empty       and __wystk aggregation
   │                     │                                 │
   ▼                     ▼                                 ▼
SYNTHESIZE                              PUBLISH
TTS adapter (ElevenLabs / OpenAI /     show-notes.md, summary.md,
Edge / your own) + pydub stitch +      segment history rolling,
SFX stingers → episode.mp3             RSS feed, static site
```

Episode artifacts land under `episodes/YYYY-MM-DD/` (mp3, transcript,
notes, manifests). The published site lands under `public/` (single
accordion `index.html`, RSS feed, audio files).

## Project layout

```
daily-personal-podcast/
├── GENERATE.md            ← instruction doc Claude reads on schedule
├── config.example.yaml    ← copy to config.yaml and customize
├── pyproject.toml         ← Python deps
│
├── app/                   ← the pipeline
│   ├── cli.py             ← `python -m app <command>`
│   ├── research.py        ← Claude Agent SDK per-segment research
│   ├── script.py          ← single-call transcript composer
│   ├── synthesize.py      ← TTS chunking + pydub stitch + SFX
│   ├── publish.py         ← show notes, history, RSS, site
│   ├── sfx.py             ← ElevenLabs sound-effects cache
│   ├── tts/               ← provider protocol + builtins
│   └── site/              ← Jinja templates + CSS + client-side JS
│
├── segments/              ← user-authored topic instructions (gitignored)
│   ├── _TEMPLATE.md       ← canonical authoring structure
│   └── _example-*.md      ← filled-in examples to copy
│
├── episodes/              ← generated artifacts (gitignored)
│   └── YYYY-MM-DD/        ← per-episode mp3, transcript, notes, history
│
├── public/                ← generated static site (gitignored)
│   ├── index.html         ← accordion of all episodes (open via file://)
│   ├── podcast.xml        ← RSS feed
│   └── episodes/          ← mp3 files
│
├── assets/                ← cached SFX stingers (gitignored)
└── tests/                 ← pytest suite
```

## Costs

For a daily ~20 minute episode with six segments:

- **ElevenLabs:** ~5,000–8,000 characters per episode → ~$0.50–$1.00/day
  on the Creator tier (or fewer thousand characters / no cost on the
  free tier if you stay under the cap).
- **Claude Agent SDK:** uses your existing Claude Max subscription if
  you have one (no marginal cost). If you instead set
  `ANTHROPIC_API_KEY`, expect roughly $1–$3 per episode depending on
  segment count and research depth.
- **SFX:** generated once and cached forever — cents, total.

You can lower costs further by switching TTS to **Edge** (free
Microsoft voices) or shrinking the segment list.

## Tests

```bash
uv run pytest -q
```

The full suite runs against deterministic fakes — no real Claude or
ElevenLabs calls — so it's fast and free.

## License

MIT. Use it, fork it, ship your own daily briefing.

## Acknowledgments

Built around [Anthropic's Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python),
[ElevenLabs](https://elevenlabs.io), [pydub](https://github.com/jiaaro/pydub),
and [feedgen](https://github.com/lkiesow/python-feedgen). The site is
plain HTML + JS with no build step.
