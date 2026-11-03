#!/bin/sh
# Schedule after the daily run's grace period, with retries for Slack outages.
set -eu
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export TZ=Australia/Sydney
cd "$(dirname "$0")"
umask 077
state_dir="${PAUSANIAS_LOG_DIR:-$HOME/.local/state/pausanias/pipeline}"
day=$(date +%F)
mkdir -p "$state_dir"
exec 9>"$state_dir/watchdog.lock"
flock -n 9 || exit 0
if [ -s "$state_dir/$day.delivered" ] || [ -f "$state_dir/$day.alerted" ]; then
  exit 0
fi
uv run cron_slack.py --status overdue --require-webhook \
  --run-id "pausanias-overdue-$day" --started-at "$(date +%s)" \
  --stage "No complete Slack report received after the 05:15 Sydney run"
touch "$state_dir/$day.alerted"
