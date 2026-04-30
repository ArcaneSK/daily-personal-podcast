# Daily Personal Podcast

A personal daily podcast generator. You author free-form markdown segments in `segments/`;
a Claude-driven pipeline researches each segment with web search, scripts a transcript,
synthesizes audio via a pluggable TTS layer (default ElevenLabs), and publishes show notes,
an RSS feed, and a static site under `docs/`.

## Setup

```bash
uv venv
uv pip install -e ".[dev]"
# Set credentials:
#   ELEVENLABS_API_KEY  (default TTS)
#   Claude credentials come from your Claude Code session (e.g., Claude Code Max).
#   Do NOT set ANTHROPIC_API_KEY — if set, the agent SDK may prefer it and bill
#   the API account instead of your Max subscription.
# Edit config.yaml — set base_url and ElevenLabs voice IDs.
```

Requires [uv](https://github.com/astral-sh/uv) and `ffmpeg` (the latter for audio stitching).

## Usage

```bash
# Generate today's episode end-to-end
uv run python -m app generate

# Or step-by-step, per the canonical lifecycle:
uv run python -m app prepare --date 2026-04-29
uv run python -m app research --date 2026-04-29
uv run python -m app script  --date 2026-04-29
uv run python -m app synthesize --date 2026-04-29
uv run python -m app publish --date 2026-04-29
```

## Authoring segments

Drop a markdown file at `segments/NN-name.md` (two-digit prefix sets order, leading
underscore disables). See `segments/_TEMPLATE.md` for the recommended structure —
designed for an LLM to fill in.

## Scheduling

Schedule a Claude Code task to read `GENERATE.md` and run it on the cadence you want
(e.g. daily). The instruction doc is portable: any agent/scaffold that runs Claude
can execute it. No machine-specific cron required.

## Spec

See [`(removed)`]((removed))
for the full design.
