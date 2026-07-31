#!/bin/sh

set -eu

MODE="${1:-push}"
LOCAL_DIR="${GRAPHIC_BOOK_LOCAL_IMAGE_DIR:-graphic_book/images}"
REMOTE="${PAUSANIAS_GRAPHIC_BOOK_REMOTE:-pausanias@raksasa:~/pausanias-graphic-book/images/}"
S3_URI="${PAUSANIAS_GRAPHIC_BOOK_S3_URI:-s3://pausanias-graphic-book-assets-849621205733}"

case "$MODE" in
  push)
    mkdir -p "$LOCAL_DIR"
    rsync -az "$LOCAL_DIR"/ "$REMOTE"
    aws s3 sync "$LOCAL_DIR"/ "$S3_URI"/images/ --only-show-errors
    ;;
  pull)
    mkdir -p "$LOCAL_DIR"
    aws s3 sync "$S3_URI"/images/ "$LOCAL_DIR"/ --only-show-errors
    rsync -az "$REMOTE" "$LOCAL_DIR"/
    ;;
  *)
    echo "Usage: $0 [push|pull]" >&2
    exit 2
    ;;
esac
