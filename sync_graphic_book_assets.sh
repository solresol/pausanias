#!/bin/sh

set -eu

MODE="${1:-pull}"
S3_URI="${PAUSANIAS_GRAPHIC_BOOK_S3_URI:-s3://pausanias-graphic-book-assets-849621205733}"

case "$MODE" in
  push|upload)
    uv run graphic_book_asset_store.py --s3-uri "$S3_URI" upload
    ;;
  pull|download)
    uv run graphic_book_asset_store.py --s3-uri "$S3_URI" pull
    ;;
  manifest)
    uv run graphic_book_asset_store.py manifest --write
    ;;
  verify)
    uv run graphic_book_asset_store.py verify
    ;;
  *)
    echo "Usage: $0 [push|pull|manifest|verify]" >&2
    exit 2
    ;;
esac
