"""Select explicit or installed serif fonts on macOS and Linux."""

import os
from pathlib import Path


def installed_font(variable: str, candidates: list[str]) -> str:
    """Honor configured fonts and fail before rendering if none is installed."""
    configured = os.environ.get(variable)
    if configured:
        candidates = [configured]
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError(f"Install a serif font or set {variable}; checked {candidates}")


BODY_FONT = installed_font(
    "PAUSANIAS_GRAPHIC_BOOK_BODY_FONT",
    [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
    ],
)
TITLE_FONT = installed_font(
    "PAUSANIAS_GRAPHIC_BOOK_TITLE_FONT",
    [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
    ],
)
DISPLAY_FONT = installed_font(
    "PAUSANIAS_GRAPHIC_BOOK_DISPLAY_FONT",
    [
        str(Path.home() / "Library/Fonts/EBGaramond-VariableFont_wght.ttf"),
        BODY_FONT,
    ],
)
