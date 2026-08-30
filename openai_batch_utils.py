"""Shared helpers for reliable OpenAI Batch API submission."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def wait_for_batch_file_processing(
    client: Any,
    file_id: str,
    *,
    timeout_seconds: float = 120.0,
    poll_seconds: float = 1.0,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Wait until an uploaded Batch API input file is ready for batch creation."""
    deadline = monotonic() + timeout_seconds
    while True:
        file_record = client.files.retrieve(file_id)
        status = getattr(file_record, "status", None)
        if status == "processed":
            return
        if status == "error":
            status_details = getattr(file_record, "status_details", None)
            detail = f": {status_details}" if status_details else ""
            raise RuntimeError(f"OpenAI batch input file {file_id} failed processing{detail}")
        if status not in {"uploaded", "pending"}:
            raise RuntimeError(
                f"OpenAI batch input file {file_id} has unexpected status {status!r}"
            )

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Timed out waiting for OpenAI batch input file {file_id} to process"
            )
        sleep(min(poll_seconds, remaining))
