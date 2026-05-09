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
