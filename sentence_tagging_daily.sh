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

# Primary lane: no-context two-flag tagger. On the Book 3 Greta/Rosie gold this
# matches ~0.69 exact vs ~0.64 for the old greta-both-context lane, at ~3x lower
# token cost per sentence (no full-passage context). See the 2026-06-13 prompt
# experiment. temperature is pinned to 0 in sentence_tag_batch.py for reproducibility.
run_batch \
  --mode greta-both \
  --use-batch-api \
  --model gpt-5.4-mini \
  --token-budget 1500000 \
  --priority-books-first 3 \
  --priority-books-last 4,8 \
  --skip-if-submitted-hours 6

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
