#!/usr/bin/env python3

"""Manage the S3-backed local cache for Pausanias graphic-book image assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_S3_URI = "s3://pausanias-graphic-book-assets-849621205733"
ASSET_ROOT_REL = Path("graphic_book") / "assets"
MANIFEST_REL = ASSET_ROOT_REL / "manifest.jsonl"
IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}


def default_s3_uri() -> str:
    return os.environ.get("PAUSANIAS_GRAPHIC_BOOK_S3_URI", DEFAULT_S3_URI)


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def normalize_s3_uri(uri: str) -> str:
    normalized = uri.rstrip("/")
    if not normalized.startswith("s3://"):
        raise ValueError(f"S3 URI must start with s3://: {uri}")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_asset_files(root: Path) -> list[Path]:
    asset_root = root / ASSET_ROOT_REL
    files: list[Path] = []

    title_page = asset_root / "pausanias-title-page.png"
    if title_page.exists():
        files.append(title_page)

    generated_root = asset_root / "generated"
    if generated_root.exists():
        files.extend(
            path
            for path in generated_root.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )

    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def manifest_row(path: Path, root: Path) -> dict[str, object]:
    asset_root = root / ASSET_ROOT_REL
    rel_path = path.relative_to(root).as_posix()
    asset_rel_path = path.relative_to(asset_root).as_posix()
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    stat = path.stat()
    return {
        "path": rel_path,
        "s3_key": f"assets/{asset_rel_path}",
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
        "media_type": media_type,
    }


def build_manifest(root: Path) -> list[dict[str, object]]:
    return [manifest_row(path, root) for path in iter_asset_files(root)]


def write_manifest(rows: Iterable[dict[str, object]], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def load_manifest(manifest_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{manifest_path}:{line_number}: invalid JSON: {exc}") from exc
    return rows


def verify_rows(rows: Iterable[dict[str, object]], root: Path) -> list[str]:
    errors: list[str] = []
    for row in rows:
        path = root / str(row["path"])
        if not path.exists():
            errors.append(f"missing: {path.relative_to(root).as_posix()}")
            continue
        expected_bytes = int(row["bytes"])
        actual_bytes = path.stat().st_size
        if actual_bytes != expected_bytes:
            errors.append(
                f"size mismatch: {path.relative_to(root).as_posix()} "
                f"expected {expected_bytes}, got {actual_bytes}"
            )
            continue
        expected_sha = str(row["sha256"])
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            errors.append(
                f"sha256 mismatch: {path.relative_to(root).as_posix()} "
                f"expected {expected_sha}, got {actual_sha}"
            )
    return errors


def s3_uri_for(base_uri: str, key: object) -> str:
    return f"{normalize_s3_uri(base_uri)}/{str(key).lstrip('/')}"


def run_aws(args: list[str]) -> None:
    printable = " ".join(shlex.quote(part) for part in ["aws", *args])
    print(f"+ {printable}", file=sys.stderr)
    subprocess.run(["aws", *args], check=True)


def upload_assets(root: Path, manifest_path: Path, s3_uri: str) -> None:
    rows = build_manifest(root)
    write_manifest(rows, manifest_path)
    for row in rows:
        run_aws(
            [
                "s3",
                "cp",
                str(root / str(row["path"])),
                s3_uri_for(s3_uri, row["s3_key"]),
                "--only-show-errors",
                "--content-type",
                str(row["media_type"]),
            ]
        )
    run_aws(
        [
            "s3",
            "cp",
            str(manifest_path),
            s3_uri_for(s3_uri, "assets/manifest.jsonl"),
            "--only-show-errors",
            "--content-type",
            "application/x-ndjson",
        ]
    )


def needs_download(root: Path, row: dict[str, object]) -> bool:
    path = root / str(row["path"])
    if not path.exists():
        return True
    if path.stat().st_size != int(row["bytes"]):
        return True
    return sha256_file(path) != str(row["sha256"])


def pull_assets(root: Path, manifest_path: Path, s3_uri: str) -> None:
    if not manifest_path.exists():
        run_aws(["s3", "cp", s3_uri_for(s3_uri, "assets/manifest.jsonl"), str(manifest_path)])
    rows = load_manifest(manifest_path)
    for row in rows:
        if not needs_download(root, row):
            continue
        local_path = root / str(row["path"])
        local_path.parent.mkdir(parents=True, exist_ok=True)
        run_aws(["s3", "cp", s3_uri_for(s3_uri, row["s3_key"]), str(local_path), "--only-show-errors"])
    errors = verify_rows(rows, root)
    if errors:
        raise RuntimeError("Pulled assets failed verification:\n" + "\n".join(errors))


def print_summary(rows: list[dict[str, object]]) -> None:
    total_bytes = sum(int(row["bytes"]) for row in rows)
    print(f"{len(rows)} asset(s), {total_bytes / 1024 / 1024:.1f} MiB")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--s3-uri", default=default_s3_uri())
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser("manifest", help="Build the local asset manifest")
    manifest_parser.add_argument("--write", action="store_true", help="Write the manifest JSONL file")

    subparsers.add_parser("verify", help="Verify local assets against the manifest")
    subparsers.add_parser("upload", help="Upload local assets and manifest to S3")
    subparsers.add_parser("pull", help="Hydrate missing or changed local assets from S3")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    manifest_path = (args.manifest or root / MANIFEST_REL).resolve()

    if args.command == "manifest":
        rows = build_manifest(root)
        print_summary(rows)
        if args.write:
            write_manifest(rows, manifest_path)
            print(f"wrote {manifest_path.relative_to(root)}")
        return

    if args.command == "verify":
        rows = load_manifest(manifest_path)
        errors = verify_rows(rows, root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            raise SystemExit(1)
        print_summary(rows)
        print("local assets match manifest")
        return

    if args.command == "upload":
        upload_assets(root, manifest_path, args.s3_uri)
        rows = load_manifest(manifest_path)
        print_summary(rows)
        print(f"uploaded assets to {normalize_s3_uri(args.s3_uri)}/assets/")
        return

    if args.command == "pull":
        pull_assets(root, manifest_path, args.s3_uri)
        rows = load_manifest(manifest_path)
        print_summary(rows)
        print(f"local assets hydrated from {normalize_s3_uri(args.s3_uri)}/assets/")
        return

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    main()
