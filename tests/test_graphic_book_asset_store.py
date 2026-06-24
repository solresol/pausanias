from pathlib import Path

import graphic_book_asset_store as store


def test_build_manifest_includes_only_graphic_book_image_assets(tmp_path: Path) -> None:
    asset_root = tmp_path / "graphic_book" / "assets"
    generated = asset_root / "generated" / "1_1_1"
    generated.mkdir(parents=True)
    (asset_root / "pausanias-title-page.png").write_bytes(b"title")
    (generated / "main.png").write_bytes(b"png")
    (generated / "source.jpg").write_bytes(b"jpg")
    (generated / "main.prompt.txt").write_text("prompt", encoding="utf-8")

    rows = store.build_manifest(tmp_path)

    assert [row["path"] for row in rows] == [
        "graphic_book/assets/generated/1_1_1/main.png",
        "graphic_book/assets/generated/1_1_1/source.jpg",
        "graphic_book/assets/pausanias-title-page.png",
    ]
    assert rows[0]["s3_key"] == "assets/generated/1_1_1/main.png"
    assert rows[2]["s3_key"] == "assets/pausanias-title-page.png"


def test_verify_rows_reports_missing_and_mismatched_files(tmp_path: Path) -> None:
    asset_root = tmp_path / "graphic_book" / "assets" / "generated" / "1_1_1"
    asset_root.mkdir(parents=True)
    image_path = asset_root / "main.png"
    image_path.write_bytes(b"original")
    rows = store.build_manifest(tmp_path)

    image_path.write_bytes(b"changed")
    errors = store.verify_rows(rows, tmp_path)

    assert len(errors) == 1
    assert errors[0].startswith("size mismatch:")
