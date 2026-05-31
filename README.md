# ElderlyBodya Radar

Daily $0 content radar for the Telegram channel **@elderlybodya** (strength /
powerlifting / bodybuilding). Pulls fresh signals from PubMed, Europe PMC, RSS,
Reddit and YouTube, ranks them with Gemini Flash, and DMs ready-to-edit post
drafts to the owner via a Telegram bot. The owner edits and publishes manually.

## Run locally (dry run, no sending)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m radar.main --dry-run
```

## Tests

```bash
.venv\Scripts\python -m pytest -q
```

## Secrets (env vars / GitHub Actions Secrets)

- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- `YOUTUBE_API_KEY`
- optional `PUBMED_API_KEY`

## Schedule

Runs daily at 06:00 MSK via GitHub Actions, and on demand via the
"Run workflow" button (`workflow_dispatch`).

## Config

Edit `config.yaml` to tweak keywords, RSS feeds, subreddits, YouTube channels,
number of drafts per day, and the Gemini model.
