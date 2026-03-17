# Agents Workspace

This folder contains multiple small, self-contained agents. Each agent follows the same structure and documentation conventions so they are easy to run, extend, and schedule.

## Standard Agent Layout

```
agents/<agent_name>/
  README.md
  <agent_name>.py
  scripts/
  digests/            # Optional output folder
```

## Conventions

- Each agent has a single runnable entrypoint `<agent_name>.py`.
- Each agent has a local `README.md` with purpose, usage, configuration, and scheduling info.
- Optional `scripts/` contains cron-ready helpers.
- Defaults should be usable without extra flags.
- Environment variables should be documented.

## Available Agents

### `news_agent`

Daily news summarizer that pulls from multiple RSS feeds, dedupes, prioritizes by recency/source diversity, and outputs a Markdown digest.

Run:

```bash
cd agents/news_agent
python3 news_agent.py
```

Topics:

```bash
python3 news_agent.py --list-topics
python3 news_agent.py --topic tech
```

Scheduler (cron-ready):

```bash
agents/news_agent/scripts/run_daily.sh
```

## Notes

If you move this repo, update any absolute paths inside agent scripts (for example in cron-ready scripts).
