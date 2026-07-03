#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$(dirname "$0")"

DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"

uv run place_state_candidate_importer.py --database-url "$DATABASE_URL"
uv run passage_place_state_batch.py --database-url "$DATABASE_URL" --fetch-batches
uv run passage_place_state_batch.py \
  --database-url "$DATABASE_URL" \
  --use-batch-api \
  --model gpt-5.4-mini \
  --token-budget 1000000 \
  --candidate-first \
  --skip-if-submitted-hours 18
