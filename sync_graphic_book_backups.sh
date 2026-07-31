#!/bin/sh

set -eu

MODE="${1:-push}"
LOCAL_IMAGE_DIR="${GRAPHIC_BOOK_LOCAL_IMAGE_DIR:-graphic_book/images}"
REMOTE_IMAGE_DIR="${PAUSANIAS_GRAPHIC_BOOK_REMOTE:-pausanias@raksasa:~/pausanias-graphic-book/images/}"
S3_URI="${PAUSANIAS_GRAPHIC_BOOK_S3_URI:-s3://pausanias-graphic-book-assets-849621205733}"

case "$MODE" in
  push)
    ./sync_graphic_book_images.sh push
    ./sync_graphic_book_assets.sh push
    ;;
  pull)
    ./sync_graphic_book_images.sh pull
    ./sync_graphic_book_assets.sh pull
    ;;
  verify)
    ./sync_graphic_book_assets.sh verify
    REMOTE_MANIFEST="$(mktemp)"
    S3_IMAGE_DIFF="$(mktemp)"
    RAKSASA_IMAGE_DIFF="$(mktemp)"
    trap 'rm -f "$REMOTE_MANIFEST" "$S3_IMAGE_DIFF" "$RAKSASA_IMAGE_DIFF"' EXIT HUP INT TERM

    aws s3 cp \
      "$S3_URI/assets/manifest.jsonl" \
      "$REMOTE_MANIFEST" \
      --only-show-errors
    cmp graphic_book/assets/manifest.jsonl "$REMOTE_MANIFEST"

    aws s3 sync \
      "$LOCAL_IMAGE_DIR/" \
      "$S3_URI/images/" \
      --dryrun >"$S3_IMAGE_DIFF"
    if [ -s "$S3_IMAGE_DIFF" ]; then
      cat "$S3_IMAGE_DIFF" >&2
      echo "S3 finished-page mirror differs from the local image tree" >&2
      exit 1
    fi

    rsync -rcn --itemize-changes \
      "$REMOTE_IMAGE_DIR" \
      "$LOCAL_IMAGE_DIR/" >"$RAKSASA_IMAGE_DIFF"
    if [ -s "$RAKSASA_IMAGE_DIFF" ]; then
      cat "$RAKSASA_IMAGE_DIFF" >&2
      echo "Raksasa finished-page mirror differs from the local image tree" >&2
      exit 1
    fi

    echo "local assets, S3 manifest, S3 pages, and raksasa pages match"
    ;;
  *)
    echo "Usage: $0 [push|pull|verify]" >&2
    exit 2
    ;;
esac
