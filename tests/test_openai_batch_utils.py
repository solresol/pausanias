from types import SimpleNamespace

import pytest

from openai_batch_utils import wait_for_batch_file_processing


class FakeFiles:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.retrieved = []

    def retrieve(self, file_id):
        self.retrieved.append(file_id)
        return SimpleNamespace(status=next(self.statuses), status_details=None)


def test_wait_for_batch_file_processing_polls_until_processed():
    files = FakeFiles(["uploaded", "processed"])
    sleeps = []

    wait_for_batch_file_processing(
        SimpleNamespace(files=files),
        "file-123",
        monotonic=iter([0.0, 0.0]).__next__,
        sleep=sleeps.append,
    )

    assert files.retrieved == ["file-123", "file-123"]
    assert sleeps == [1.0]


def test_wait_for_batch_file_processing_rejects_file_errors():
    files = FakeFiles(["error"])

    with pytest.raises(RuntimeError, match="failed processing"):
        wait_for_batch_file_processing(SimpleNamespace(files=files), "file-123")


def test_wait_for_batch_file_processing_times_out():
    files = FakeFiles(["uploaded", "uploaded"])

    with pytest.raises(TimeoutError, match="Timed out"):
        wait_for_batch_file_processing(
            SimpleNamespace(files=files),
            "file-123",
            timeout_seconds=1.0,
            monotonic=iter([0.0, 0.0, 1.0]).__next__,
            sleep=lambda _seconds: None,
        )


def test_wait_for_batch_file_processing_rejects_unknown_status():
    files = FakeFiles([None])

    with pytest.raises(RuntimeError, match="unexpected status"):
        wait_for_batch_file_processing(SimpleNamespace(files=files), "file-123")
