# Daily cron reports in Slack

The first increment posts two short reports: `STARTED`, then `SUCCEEDED` or
`FAILED`. Success is reported only after the final website rsync exits zero.
Each report includes `job: pausanias-daily`, a unique run ID, UTC timestamp,
elapsed time, host, checkout commit, stage, and exit code. Cron mail remains
available for actionable output. Slack delivery failures do not change the
pipeline exit code. A killed host/process may have no final report.

## Prepared quieter cron output

The preparation branch retains full output in private per-run logs under
`$HOME/.local/state/pausanias/pipeline/` (files mode `600`). Exact known empty-queue
notices stay in the log. The predictor, network and site producers use
`cron_reporting.routine_report()` at known routine reporting sites, including
multiline evaluation tables and Greek coefficient rows. The cron wrapper opts
in through `cron_output.py --website-stats`; interactive output is unchanged.
Unmarked output, warnings, stderr and zero-exit failure diagnostics remain visible
in cron mail. Failure to append a routine report falls back to visible output and
a warning. The wrapper preserves the command's exit and signal status.

When adding a producer report, use `routine_report()` only for normal progress,
statistics or generated-page summaries. Leave unexpected states and actionable
diagnostics on ordinary stdout/stderr. This keeps new unknown output visible by
default rather than guessing its meaning from table formatting or keywords.

## Configure on raksasa

Create a Slack app with an incoming webhook for the chosen reporting channel.
Store its URL as a single line in
`/home/pausanias/.config/pausanias/slack-webhook`, owned by `pausanias`, with
directory mode `700` and file mode `600`. Do not put the URL in Git or cron mail.
The notifier is inactive if that file does not exist. Override the path with
`PAUSANIAS_SLACK_WEBHOOK_FILE` if needed.

Preview the report without posting or running the pipeline:

```sh
uv run cron_slack.py --dry-run --status started --run-id setup-preview \
  --started-at "$(date +%s)" --stage setup
```

To test actual delivery, use the same command without `--dry-run`. Keep the
test run ID distinct from scheduled runs so a future monitor cannot mistake a
setup message for daily pipeline completion.

## Later daily checklist

A monitor should check for `SUCCEEDED` for each registered job, using the run
ID to match start and completion. For Pausanias the expected schedule is daily
at 05:15 Australia/Sydney; allow runtime/grace before declaring it overdue.
Register further jobs by stable job key, schedule/time zone, grace period,
channel, and investigation runbook. Ordinary channel messages and `STARTED`
reports must not satisfy the successful-completion check.

Streaming log chunks, threaded updates, and the monitoring automation are
subsequent increments.
