"""Explicit routine reports: normal print interactively, private log in cron."""
from __future__ import annotations

import os
import stat
import sys

ROUTINE_LOG_ENV = "PAUSANIAS_ROUTINE_REPORT_LOG"
_warned = False


def routine_report(*values, sep=" ", end="\n", file=None, flush=False):
    """Mark a known report, leaving all unmarked output and stderr alone.

    Only cron_output's --website-stats opt-in supplies a private existing log.
    Invalid/unavailable sinks fall back to ordinary output with a visible warning.
    No content/keyword filtering is applied to predictor tables or generated stats.
    """
    global _warned
    destination = os.environ.get(ROUTINE_LOG_ENV)
    if not destination or file not in (None, sys.stdout):
        print(*values, sep=sep, end=end, file=file, flush=flush)
        return
    descriptor = None
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise OSError("Routine report sink is not an owned private regular file")
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            descriptor = None
            print(*values, sep=sep, end=end, file=stream, flush=True)
    except OSError:
        if not _warned:
            print("Warning: private routine-report logging failed; retaining reports in cron output.", file=sys.stderr)
            _warned = True
        print(*values, sep=sep, end=end, file=file, flush=flush)
    finally:
        if descriptor is not None:
            os.close(descriptor)
