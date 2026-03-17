# News Agent (Python)

A lightweight, agentic daily news summarizer that pulls from multiple RSS feeds, dedupes, prioritizes by recency and source diversity, and produces a Markdown digest.

## Run

```bash
python3 news_agent.py
```

Write to a file:

```bash
python3 news_agent.py --out /tmp/digest.md
```

## Topics

Available topics:

- `world`
- `tech`
- `finance`

Example:

```bash
python3 news_agent.py --topic tech
```

You can also list topics:

```bash
python3 news_agent.py --list-topics
```

## LLM Summaries (Optional)

By default, summaries are extractive. You can enable LLM-based abstractive summaries with the OpenAI Python SDK:

```bash
pip install openai
export OPENAI_API_KEY=...
NEWS_SUMMARY_MODE=llm NEWS_LLM_MODEL=gpt-5 python3 news_agent.py --topic world
```

If the SDK isn't installed or the API call fails, it falls back to extractive summaries.

## Environment Variables

- `NEWS_WINDOW_HOURS` (default `24`)
- `NEWS_MAX_ITEMS` (default `12`)
- `NEWS_OUT` (default empty; if set, writes to that path)
- `NEWS_TOPIC` (default `world`)
- `NEWS_SUMMARY_MODE` (default `extractive`, options: `extractive`, `llm`)
- `NEWS_LLM_MODEL` (default `gpt-5`)

Example:

```bash
NEWS_WINDOW_HOURS=36 NEWS_MAX_ITEMS=20 NEWS_OUT=/tmp/digest.md python3 news_agent.py
```

## Cron-Ready Scheduler

A cron-ready script is included at `scripts/run_daily.sh`. It writes digests to `digests/` with a date-based filename.

Example crontab entry (runs at 7:15 AM local time):

```bash
15 7 * * * /Users/akshataraikar/Downloads/REPOS/agents/news_agent/scripts/run_daily.sh
```

If you move the repo, update `BASE_DIR` inside `scripts/run_daily.sh`.

## Customize Sources

Edit `DEFAULT_SOURCES` or `SOURCES_BY_TOPIC` in `news_agent.py` to add or remove RSS feeds.
