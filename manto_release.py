"""Helpers for discovering and caching public MANTO Zenodo releases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ZENODO_API_BASE = "https://zenodo.org/api"
MANTO_CONCEPT_RECORD_ID = 19446254
DEFAULT_CACHE_DIR = Path("tmp") / "manto-releases"


@dataclass(frozen=True)
class MantoRelease:
    record_id: int
    concept_record_id: int | None
    doi: str
    concept_doi: str
    version: str
    title: str
    created: str
    modified: str
    license_id: str
    file_key: str
    file_size: int
    file_checksum: str
    file_url: str
    metadata: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_latest_release(
    *,
    concept_record_id: int = MANTO_CONCEPT_RECORD_ID,
    api_base: str = ZENODO_API_BASE,
    timeout: int = 60,
) -> MantoRelease:
    """Return the most recent Zenodo record for the MANTO concept record."""
    response = requests.get(
        f"{api_base.rstrip('/')}/records",
        params={
            "q": f"conceptrecid:{concept_record_id}",
            "sort": "mostrecent",
            "size": 1,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        raise RuntimeError(f"No MANTO releases found for conceptrecid:{concept_record_id}")
    return release_from_zenodo_record(hits[0])


def release_from_zenodo_record(record: dict[str, Any]) -> MantoRelease:
    """Normalize a Zenodo API record into the release fields used by the repo."""
    files = record.get("files") or []
    zip_files = [file for file in files if str(file.get("key", "")).lower().endswith(".zip")]
    if not zip_files:
        raise ValueError(f"Zenodo record {record.get('id')} has no ZIP file")
    file_info = zip_files[0]
    metadata = record.get("metadata") or {}
    license_info = metadata.get("license") or {}
    links = file_info.get("links") or {}
    file_url = links.get("self") or links.get("download")
    if not file_url:
        raise ValueError(f"Zenodo record {record.get('id')} ZIP file has no download URL")
    return MantoRelease(
        record_id=int(record["id"]),
        concept_record_id=int(record["conceptrecid"]) if record.get("conceptrecid") else None,
        doi=record.get("doi") or "",
        concept_doi=record.get("conceptdoi") or "",
        version=metadata.get("version") or "",
        title=metadata.get("title") or "",
        created=record.get("created") or "",
        modified=record.get("modified") or "",
        license_id=license_info.get("id") or "",
        file_key=file_info.get("key") or "",
        file_size=int(file_info.get("size") or 0),
        file_checksum=file_info.get("checksum") or "",
        file_url=file_url,
        metadata=record,
    )


def release_zip_path(release: MantoRelease, cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    return cache_dir / str(release.record_id) / release.file_key


def checksum_matches(path: Path, checksum: str) -> bool:
    if not checksum:
        return True
    algorithm, _, expected = checksum.partition(":")
    if not algorithm or not expected:
        algorithm = "md5"
        expected = checksum
    algorithm = algorithm.lower()
    if algorithm != "md5":
        raise ValueError(f"Unsupported release checksum algorithm: {algorithm}")
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.lower()


def download_release(
    release: MantoRelease,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    timeout: int = 120,
) -> Path:
    """Download a release ZIP to the local cache and verify its checksum."""
    target = release_zip_path(release, cache_dir)
    if target.exists() and not force:
        if checksum_matches(target, release.file_checksum):
            return target
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(target.suffix + ".part")
    with requests.get(release.file_url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with tmp_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp_path.replace(target)
    if not checksum_matches(target, release.file_checksum):
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch after downloading {release.file_key}")
    return target


def release_json(release: MantoRelease) -> str:
    payload = {
        "record_id": release.record_id,
        "concept_record_id": release.concept_record_id,
        "doi": release.doi,
        "concept_doi": release.concept_doi,
        "version": release.version,
        "title": release.title,
        "created": release.created,
        "modified": release.modified,
        "license_id": release.license_id,
        "file_key": release.file_key,
        "file_size": release.file_size,
        "file_checksum": release.file_checksum,
        "file_url": release.file_url,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
