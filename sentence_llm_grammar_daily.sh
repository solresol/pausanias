#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

cd "$(dirname "$0")"

DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"
SSH_HOST="${PAUSANIAS_SSH_HOST:-}"
MODEL="${PAUSANIAS_LLM_GRAMMAR_MODEL:-gpt-5.4-mini}"
PROMPT_VERSION="${PAUSANIAS_LLM_GRAMMAR_PROMPT_VERSION:-greek-sentence-grammar-v1}"
DAILY_TOKEN_BUDGET="${PAUSANIAS_LLM_GRAMMAR_DAILY_TOKEN_BUDGET:-1000000}"
BUDGET_TIMEZONE="${PAUSANIAS_LLM_GRAMMAR_BUDGET_TIMEZONE:-Australia/Sydney}"
CONCURRENCY="${PAUSANIAS_LLM_GRAMMAR_CONCURRENCY:-1}"
WRITE_BATCH_SIZE="${PAUSANIAS_LLM_GRAMMAR_WRITE_BATCH_SIZE:-1}"
MAX_FAILURES="${PAUSANIAS_LLM_GRAMMAR_MAX_FAILURES:-10}"
SAMPLE_SEED="${PAUSANIAS_LLM_GRAMMAR_SAMPLE_SEED:-sentence-llm-grammar-daily-$(date +%Y-%m-%d)}"
STOP_AFTER="${PAUSANIAS_LLM_GRAMMAR_STOP_AFTER:-}"

run_grammar() {
  if [ -n "$SSH_HOST" ]; then
    uv run sentence_llm_grammar.py --database-url "$DATABASE_URL" --ssh-host "$SSH_HOST" "$@"
  else
    uv run sentence_llm_grammar.py --database-url "$DATABASE_URL" "$@"
  fi
}

if [ -n "$STOP_AFTER" ]; then
  run_grammar \
    --model "$MODEL" \
    --prompt-version "$PROMPT_VERSION" \
    --daily-token-budget "$DAILY_TOKEN_BUDGET" \
    --budget-timezone "$BUDGET_TIMEZONE" \
    --random-order \
    --sample-seed "$SAMPLE_SEED" \
    --concurrency "$CONCURRENCY" \
    --write-batch-size "$WRITE_BATCH_SIZE" \
    --max-failures "$MAX_FAILURES" \
    --stop-after "$STOP_AFTER"
else
  run_grammar \
    --model "$MODEL" \
    --prompt-version "$PROMPT_VERSION" \
    --daily-token-budget "$DAILY_TOKEN_BUDGET" \
    --budget-timezone "$BUDGET_TIMEZONE" \
    --random-order \
    --sample-seed "$SAMPLE_SEED" \
    --concurrency "$CONCURRENCY" \
    --write-batch-size "$WRITE_BATCH_SIZE" \
    --max-failures "$MAX_FAILURES"
fi
