#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$(dirname "$0")"

DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"
SSH_HOST="${PAUSANIAS_SSH_HOST:-}"
MODEL="${PAUSANIAS_SECTION_PEOPLE_MODEL:-gpt-5.4-mini}"
PROMPT_VERSION="${PAUSANIAS_SECTION_PEOPLE_PROMPT_VERSION:-section-people-v1}"
TOKEN_BUDGET="${PAUSANIAS_SECTION_PEOPLE_TOKEN_BUDGET:-100000}"
TOKENS_PER_SECTION="${PAUSANIAS_SECTION_PEOPLE_TOKENS_PER_SECTION:-2500}"
RANDOM_SEED="${PAUSANIAS_SECTION_PEOPLE_RANDOM_SEED:-section-people-v1}"
SKIP_IF_SUBMITTED_HOURS="${PAUSANIAS_SECTION_PEOPLE_SKIP_IF_SUBMITTED_HOURS:-18}"

run_people_batch() {
  if [ -n "$SSH_HOST" ]; then
    uv run section_people_batch.py --database-url "$DATABASE_URL" --ssh-host "$SSH_HOST" "$@"
  else
    uv run section_people_batch.py --database-url "$DATABASE_URL" "$@"
  fi
}

run_people_batch \
  --fetch-batches \
  --prompt-version "$PROMPT_VERSION"

run_people_batch \
  --use-batch-api \
  --model "$MODEL" \
  --prompt-version "$PROMPT_VERSION" \
  --token-budget "$TOKEN_BUDGET" \
  --tokens-per-section "$TOKENS_PER_SECTION" \
  --random-seed "$RANDOM_SEED" \
  --skip-if-submitted-hours "$SKIP_IF_SUBMITTED_HOURS"
