#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$(dirname "$0")"

DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"
SSH_HOST="${PAUSANIAS_SSH_HOST:-}"

run_batch() {
  if [ -n "$SSH_HOST" ]; then
    uv run sentence_tag_batch.py --database-url "$DATABASE_URL" --ssh-host "$SSH_HOST" "$@"
  else
    uv run sentence_tag_batch.py --database-url "$DATABASE_URL" "$@"
  fi
}

run_batch --fetch-batches

# "greta-inspired-myth-history-other": the calibrated two-flag tagger (no context,
# temperature 0). On the Book 3 Greta/Rosie gold it best matches her mythic/historical/
# other base rates (calib gap 12% vs 17% for the original) and is the most precise.
# The abandoned greta-both-context lane has been removed. See the 2026-06-13 experiment.
run_batch \
  --mode greta-both \
  --use-batch-api \
  --model gpt-5.4-mini \
  --token-budget 1500000 \
  --priority-books-first 3 \
  --priority-books-last 4,8 \
  --skip-if-submitted-hours 6

# "original-myth-history-other": the simple forced single-label tagger (the original
# prompt). Kept as the second classifier so we can compare it against greta-inspired.
run_batch \
  --mode greta \
  --use-batch-api \
  --model gpt-5.4-mini \
  --token-budget 500000 \
  --priority-books-last 4,8 \
  --skip-if-submitted-hours 6

run_batch \
  --mode legacy \
  --use-batch-api \
  --model gpt-5 \
  --stop-after 5 \
  --priority-books-last 4,8 \
  --skip-if-submitted-hours 6
