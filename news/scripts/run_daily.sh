#!/bin/sh
# Cron-ready daily run script.
set -eu

BASE_DIR="/Users/akshataraikar/Downloads/REPOS/agents/news"
PYTHON_BIN="/usr/bin/python3"
OUT_DIR="$BASE_DIR/digests"
TOPIC="${NEWS_TOPIC:-world}"
SUMMARY_MODE="${NEWS_SUMMARY_MODE:-extractive}"
LLM_MODEL="${NEWS_LLM_MODEL:-gpt-5}"

mkdir -p "$OUT_DIR"
DATE_STR="$(date +%F)"
OUT_FILE="$OUT_DIR/${TOPIC}-${DATE_STR}.md"

cd "$BASE_DIR"
$PYTHON_BIN agent.py \
  --topic "$TOPIC" \
  --summary-mode "$SUMMARY_MODE" \
  --llm-model "$LLM_MODEL" \
  --out "$OUT_FILE"
