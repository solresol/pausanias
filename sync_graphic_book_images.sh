#!/bin/sh

set -eu

MODE="${1:-push}"
LOCAL_DIR="${GRAPHIC_BOOK_LOCAL_IMAGE_DIR:-graphic_book/images}"
REMOTE="${PAUSANIAS_GRAPHIC_BOOK_REMOTE:-pausanias@raksasa:~/pausanias-graphic-book/images/}"

case "$MODE" in
  push)
    mkdir -p "$LOCAL_DIR"
    rsync -az "$LOCAL_DIR"/ "$REMOTE"
    if [ -n "${PAUSANIAS_GRAPHIC_BOOK_S3_URI:-}" ]; then
      aws s3 sync "$LOCAL_DIR"/ "$PAUSANIAS_GRAPHIC_BOOK_S3_URI"/images/
    fi
    ;;
  pull)
    mkdir -p "$LOCAL_DIR"
    rsync -az "$REMOTE" "$LOCAL_DIR"/
    ;;
  *)
    echo "Usage: $0 [push|pull]" >&2
    exit 2
    ;;
esac
