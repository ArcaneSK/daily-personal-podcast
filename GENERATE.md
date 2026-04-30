# Daily podcast generation — instructions for Claude

You are generating today's episode of a personal daily podcast.
This document is the entire spec for what to do; do not skip steps.

## Preconditions (verify, don't assume)
- Repository is the current working directory.
- `uv run python -m app --version` succeeds. If not, run `uv pip install -e .` and retry.
- `config.yaml` exists. If not, stop and surface the issue.
- Required env vars are set per `config.yaml: tts.provider`.
  Default (ElevenLabs): `ELEVENLABS_API_KEY`.
  Claude credentials come from the host environment's Claude Code session.
  Do NOT set `ANTHROPIC_API_KEY` — if it is set, the agent SDK may prefer it and bill the API
  account instead of the Claude subscription.
- Today's episode dir does not yet have an `episode.mp3`. If it does, stop unless invoked with `--force`.
- A clean working tree is **not** required. The pipeline only writes inside `episodes/`,
  `segments/_history/`, and `docs/`; any uncommitted changes elsewhere (e.g. segment edits
  the user made today) are left alone and excluded from the auto-commit.

## Steps
1. Run `python -m app generate`.
2. If any step fails, do NOT start over. Re-run only the failed step. The pipeline is idempotent and resumable.
3. On segments that classify as `empty` or `blurb` (in run-manifest.json), continue. The pipeline drops empty segments and rolls blurbs into a "What you should know today" mini-segment automatically. Do not retry indefinitely.
4. After `publish` completes, verify these files exist:
   - episodes/YYYY-MM-DD/episode.mp3
   - episodes/YYYY-MM-DD/show-notes.md
   - episodes/YYYY-MM-DD/summary.md
   - docs/podcast.xml (modified today)
   - docs/episodes/YYYY-MM-DD/index.html
5. Commit only the pipeline's output paths with message `Episode YYYY-MM-DD`:
   `git add episodes/YYYY-MM-DD/ episodes/_recent.md segments/_history/ docs/` then commit.
   This avoids sweeping in unrelated user changes (e.g. segment authoring in progress) and
   keeps the precondition lightweight — no stash, no clean-tree gate. If nothing is staged
   after `git add` (e.g. on re-runs where outputs are already committed), skip the commit
   rather than producing an empty one. Do not push.

## Failure modes
- Claude Code session missing or expired → stop, surface clearly. Do NOT set `ANTHROPIC_API_KEY` to work around this.
- TTS provider auth missing → stop, surface clearly.
- Web search returns nothing for a segment → expected occasionally; segment is classified `empty` and skipped (or rolled into `__wystk` if `blurb`).
- mp3 ends up under 60 seconds → likely synthesis bug; do not publish, surface for review.

## Do not
- Edit segment markdown files. Authoring is the user's job.
- Push or open PRs. Commit only.
- Re-run `generate` after a successful publish; one episode per day.
