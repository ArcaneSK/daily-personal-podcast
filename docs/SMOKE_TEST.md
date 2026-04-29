# Manual smoke test — first real episode

Before scheduling, verify the pipeline end-to-end against real APIs with a single small segment.

## Prep
1. `uv venv && uv pip install -e ".[dev]"` and confirm `ffmpeg` is on PATH (`ffmpeg -version`).
2. Set `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY` in your shell.
3. Edit `config.yaml`:
   - Set `podcast.base_url` to your eventual public URL (GitHub Pages or otherwise).
   - Replace the three `voice_id` placeholders with real ElevenLabs voice IDs.
4. Disable all but one segment by renaming others with a leading underscore (e.g.
   `_02-ai-news.md`). Leave `02-ai-news.md` (or whichever you want to test) active.

## Run
```bash
uv run python -m app generate
```

## Verify
- `episodes/<date>/episode.mp3` is between 30s and 10min.
- `episodes/<date>/show-notes.md` lists 1+ stories with `[source]` links.
- `episodes/<date>/transcript.md` reads cleanly — no hallucinated URLs in spoken text.
- `docs/index.html` loads in a browser; the audio player plays.
- `docs/podcast.xml` validates against an online RSS validator (e.g. cast feed validators).

## Iterate
- Tone wrong? Adjust persona strings in `config.yaml`.
- Too long/short? Adjust `target_total_minutes` and individual segment durations in segment prose.
- Wrong topical focus? Tighten the "What to cover" / "What to skip" sections in the segment file.

When happy with one segment, re-enable the rest and run again.
