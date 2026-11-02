#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$(dirname "$0")"

# Slack is additive: retain cron output and the pipeline's original exit status.
cron_started_at=$(date +%s)
cron_run_id="pausanias-daily-$(date -u +%Y%m%dT%H%M%SZ)-$$"
cron_stage=checkout
umask 077
cron_log_dir="${PAUSANIAS_LOG_DIR:-$HOME/.local/state/pausanias/pipeline}"
mkdir -p "$cron_log_dir"
cron_log="$cron_log_dir/$cron_run_id.log"
if command -v flock >/dev/null 2>&1; then
  exec 9>"${PAUSANIAS_PIPELINE_LOCKFILE:-daily_pipeline.lock}"
  if ! flock -n 9; then
    printf '%s\n' 'Daily pipeline already running; no duplicate work started.' >> "$cron_log"
    exit 0
  fi
fi
run_logged() {
  uv run cron_output.py --log "$cron_log" --stage "$cron_stage" -- "$@"
}
run_website_stats() {
  uv run cron_output.py --log "$cron_log" --stage "$cron_stage" --website-stats -- "$@"
}
notify_slack() {
  if ! uv run cron_slack.py --status "$1" --exit-code "$2" \
      --run-id "$cron_run_id" --started-at "$cron_started_at" --stage "$cron_stage"; then
    echo "Warning: Slack notification failed; see cron output for pipeline status." >&2
  fi
}
finish_cron() {
  cron_exit_code=$1
  trap - 0
  if [ "$cron_exit_code" -eq 0 ]; then
    notify_slack succeeded "$cron_exit_code"
  else
    notify_slack failed "$cron_exit_code"
  fi
  exit "$cron_exit_code"
}
trap 'finish_cron $?' 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
notify_slack started 0
run_logged git pull -q

export PAUSANIAS_DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"
GRAPHIC_BOOK_IMAGE_DIR="${GRAPHIC_BOOK_IMAGE_DIR:-$HOME/pausanias-graphic-book/images}"
if [ ! -d "$GRAPHIC_BOOK_IMAGE_DIR" ]; then
  GRAPHIC_BOOK_IMAGE_DIR="graphic_book/images"
fi

cron_stage=analysis
PAUSANIAS_QUIET_EMPTY=1 run_logged uv run mythic_sceptic_analyser.py --stop 50
PAUSANIAS_QUIET_EMPTY=1 run_logged uv run extract_proper_nouns.py --stop 50
run_logged uv run link_wikidata.py --stop-after 100
run_logged uv run translate_pausanias.py --stop 50
run_logged uv run split_sentences.py --model gpt-5.6-luna --stop 200
run_logged uv run summarise_passages.py --stop-after 50
run_website_stats uv run find_predictors.py
run_website_stats uv run find_sentence_predictors.py
run_website_stats uv run analyse_noun_network.py
cron_stage=sentence-tagging
run_logged ./sentence_tagging_daily.sh
cron_stage=sentence-grammar
run_logged ./sentence_llm_grammar_daily.sh
cron_stage=section-people
run_logged ./section_people_daily.sh
cron_stage=place-state
run_logged ./passage_place_state_daily.sh
cron_stage=graphic-book-sync
AWS_PROFILE="${PAUSANIAS_GRAPHIC_BOOK_AWS_PROFILE:-pausanias-graphic-book}" \
  AWS_SHARED_CREDENTIALS_FILE="${PAUSANIAS_GRAPHIC_BOOK_AWS_CREDENTIALS:-$HOME/.aws/credentials.pausanias-exchange}" \
  run_logged uv run graphic_book_exchange.py sync --image-dir "$GRAPHIC_BOOK_IMAGE_DIR"
cron_stage=website
run_website_stats uv run create_website.py --graphic-book-image-dir "$GRAPHIC_BOOK_IMAGE_DIR"
cron_stage=graphic-book-build
run_website_stats uv run build_graphic_book.py --image-dir "$GRAPHIC_BOOK_IMAGE_DIR" --output-dir pausanias_site/graphic-book
cron_stage=publish
run_logged rsync -az pausanias_site/ merah:/var/www/vhosts/pausanias.symmachus.org/htdocs/
