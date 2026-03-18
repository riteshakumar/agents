# Agents Workspace

This folder contains multiple small, self-contained agents. Each agent follows the same structure and documentation conventions so they are easy to run, extend, and schedule.

## Standard Agent Layout

```
agents/<agent_name>/
  README.md
  agent.py
  scripts/
  digests/            # Optional output folder
```

Shared helpers live in:

```
agents/_shared/
```

Use the template to bootstrap new agents:

```
agents/template/
```

Or generate one quickly:

```
scripts/new_agent.sh <agent_name>
```

## Conventions

- Each agent has a single runnable entrypoint `<agent_name>.py`.
- Each agent has a local `README.md` with purpose, usage, configuration, and scheduling info.
- Optional `scripts/` contains cron-ready helpers.
- Defaults should be usable without extra flags.
- Environment variables should be documented.

## Available Agents

### `news`

Daily news summarizer that pulls from multiple RSS feeds, dedupes, prioritizes by recency/source diversity, and outputs a Markdown digest.

Run:

```bash
cd agents/news
python3 agent.py
```

Topics:

```bash
python3 agent.py --list-topics
python3 agent.py --topic tech
```

Scheduler (cron-ready):

```bash
agents/news/scripts/run_daily.sh
```

### `mcp`

Minimal example of a tool-connected agent using the Model Context Protocol (MCP). Includes a server exposing tools and a client that calls them.

Run server:

```bash
cd agents/mcp
python3 server.py
```

Run client:

```bash
python3 agent.py --demo

### `template`

Starter scaffold for creating new agents quickly.
```

## Notes

If you move this repo, update any absolute paths inside agent scripts (for example in cron-ready scripts).
