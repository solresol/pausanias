#!/bin/sh

set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

cd "$(dirname "$0")"

# Preserve the pipeline exit status and record Slack delivery separately.
cron_started_at=$(date +%s)
cron_run_id="pausanias-daily-$(date -u +%Y%m%dT%H%M%SZ)-$$"
cron_stage=checkout
cron_day=$(TZ=Australia/Sydney date +%F)
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
  slack_status=$1
  slack_exit=$2
  shift 2
  uv run cron_slack.py --status "$slack_status" --exit-code "$slack_exit" \
      --run-id "$cron_run_id" --started-at "$cron_started_at" --stage "$cron_stage" --require-webhook "$@"
}
finish_cron() {
  cron_exit_code=$1
  trap - 0
  if [ "$cron_exit_code" -eq 0 ]; then
    final_status=succeeded
  else
    final_status=failed
  fi
  if notify_slack "$final_status" "$cron_exit_code" --log "$cron_log"; then
    printf '%s %s\n' "$final_status" "$cron_run_id" > "$cron_log_dir/.$cron_run_id"
    mv "$cron_log_dir/.$cron_run_id" "$cron_log_dir/$cron_day.delivered"
  else
    echo "Slack delivery incomplete. Full output: $cron_log" >&2
  fi
  exit "$cron_exit_code"
}
trap 'finish_cron $?' 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
notify_slack started 0 || echo "Slack start notification failed." >&2
run_logged git pull -q

export PAUSANIAS_DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"
GRAPHIC_BOOK_IMAGE_DIR="${GRAPHIC_BOOK_IMAGE_DIR:-$HOME/pausanias-graphic-book/images}"
if [ ! -d "$GRAPHIC_BOOK_IMAGE_DIR" ]; then
  GRAPHIC_BOOK_IMAGE_DIR="graphic_book/images"
fi

cron_stage=analysis
run_logged uv run mythic_sceptic_analyser.py --stop 50
run_logged uv run extract_proper_nouns.py --stop 50
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
