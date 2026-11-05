#!/usr/bin/env python3
"""Render 1.28.7 only from the independently verified corrected corpus contract."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys


def main() -> None:
    """Fail closed on stale source, missing authority or changed component art."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    root = args.repository_root.resolve()
    contract_path = args.contract or root / 'graphic_book/assets/generated/1_28_7/revisions/20261105-correction/correction_contract.json'
    assets = contract_path.parent
    contract = json.loads(contract_path.read_text())
    if contract['status'] != 'authoritative-corrected-export-verified':
        raise RuntimeError('Corrected authoritative corpus/hash not yet supplied; no render authorized')
    for field in ('expected_source_sha256', 'expected_translation_utf8_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', contract.get(field) or ''):
            raise RuntimeError('Missing authoritative hash: ' + field)
    if contract['expected_source_sha256'] == contract['stale_source_sha256']:
        raise RuntimeError('The stale source hash cannot authorize a corrected page')
    sys.path.insert(0, str(root))
    from graphic_book_corpus import load_translation, snapshot_path
    from graphic_book_exchange import source_hash
    from graphic_book import render_passage_1_28_7 as layout

    def verified_translation(passage_id: str) -> str:
        if passage_id != contract['passage_id']:
            raise RuntimeError('Correction is scoped only to 1.28.7')
        snapshot = snapshot_path()
        with sqlite3.connect(snapshot.as_uri() + '?mode=ro', uri=True) as conn:
            row = conn.execute('SELECT greek_text,english_translation,source_sha256 FROM translations WHERE passage_id=?', (passage_id,)).fetchone()
            exported_at = conn.execute('SELECT exported_at FROM metadata WHERE singleton=1').fetchone()[0]
        if not row or source_hash(row[0], row[1]) != row[2]:
            raise RuntimeError('Exported Greek/English source hash is inconsistent')
        if row[2] != contract['expected_source_sha256'] or exported_at != contract['expected_exported_at']:
            raise RuntimeError('Snapshot is not the owner-verified corrected export')
        passage = load_translation(passage_id)
        if hashlib.sha256(passage.encode()).hexdigest() != contract['expected_translation_utf8_sha256']:
            raise RuntimeError('Corrected English differs from the authoritative contract')
        if not passage.startswith(contract['preserved_english_prefix']):
            raise RuntimeError('Surrounding English was changed beyond the authorized correction')
        if 'after the death of Mecisteus' in passage or 'Oedipus himself went to Thebes' in passage:
            raise RuntimeError('Reversed funeral-games roles remain in the source')
        return passage

    verified_translation('1.28.7')
    art = assets / 'tomb_study.png'
    if hashlib.sha256(art.read_bytes()).hexdigest() != contract['reuse_component_sha256']:
        raise RuntimeError('Reused accurate art differs from its preserved component hash')
    layout.ASSETS = assets
    layout.load_translation = verified_translation
    output = args.output or assets / 'candidate.png'
    if root / 'graphic_book/images' in output.resolve().parents:
        raise RuntimeError('Review the correction outside the canonical page tree first')
    layout.render(output, args.preflight)
    report_path = assets / 'layout_report.json'
    report = json.loads(report_path.read_text())
    report['correction'] = {
        'supersedes_result_id': contract['stale_result_id'],
        'expected_source_sha256': contract['expected_source_sha256'],
        'expected_exported_at': contract['expected_exported_at'],
        'stale_source_rejected': True,
        'surrounding_english_preserved': True,
        'art_reused_without_change': True,
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
