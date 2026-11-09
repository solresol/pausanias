#!/usr/bin/env python
"""Prepare an immutable Epimanto release locally; never connect or publish.

Upload the _releases directory first, then the root index.html as the final
single-file switch. All assets remain within the approved htdocs directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ASSETS = {'index.html', 'style.css', 'app.js', 'data.json', 'data.js'}
REFERENCES = {'style.css', 'app.js', 'data.js', 'data.json', 'manifest.json'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Required regular file missing or symlinked: {name}')
    return path.read_bytes()


def prepare_release(source, output):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; never replace an existing release bundle')
    manifest_bytes = read_regular(source, 'manifest.json')
    manifest = json.loads(manifest_bytes)
    if (not isinstance(manifest, dict)
        or set(manifest) != {'schema_version', 'release_record_id', 'files'}
        or manifest.get('schema_version') != 1
        or not isinstance(manifest.get('files'), dict)
        or set(manifest['files']) != ASSETS):
        raise ValueError('Unsupported or unsafe source manifest')
    record_id = manifest.get('release_record_id')
    if type(record_id) is not int or record_id <= 0:
        raise ValueError('Invalid pinned MANTO release ID')
    files = {}
    for name in sorted(ASSETS):
        expected = manifest['files'][name]
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError(f'Invalid checksum for {name}')
        files[name] = read_regular(source, name)
        if sha256(files[name]) != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    payload = json.loads(files['data.json'])
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        raise ValueError('Unsupported snapshot schema')
    if payload.get('release', {}).get('record_id') != record_id:
        raise ValueError('Snapshot and manifest release IDs disagree')
    digest = sha256(manifest_bytes)
    release_name = f'{record_id}-{digest}'
    prefix = f'_releases/{release_name}/'
    html = files['index.html'].decode('utf-8')
    seen = set()
    pattern = re.compile(r'(?P<attr>src|href)="(?P<name>' + '|'.join(re.escape(n) for n in sorted(REFERENCES)) + ')"')
    def replace(match):
        name = match['name']
        seen.add(name)
        return f'{match["attr"]}="{prefix}{name}"'
    entrypoint = pattern.sub(replace, html)
    if seen != REFERENCES or entrypoint.count('</head>') != 1:
        raise ValueError('Source entrypoint asset references changed; review before packaging')
    entrypoint = entrypoint.replace('</head>', f'<meta name="epimanto-release" content="{release_name}">\n</head>')
    entrypoint_bytes = entrypoint.encode('utf-8')
    # All validation precedes directory creation. No credentials or network calls.
    output.mkdir(parents=True, exist_ok=False)
    release_dir = output / prefix
    release_dir.mkdir(parents=True)
    for name, content in files.items():
        (release_dir / name).write_bytes(content)
    (release_dir / 'manifest.json').write_bytes(manifest_bytes)
    (output / 'index.html').write_bytes(entrypoint_bytes)
    result = {
        'schema_version': 1,
        'release_record_id': record_id,
        'release_name': release_name,
        'asset_prefix': prefix,
        'source_manifest_sha256': digest,
        'entrypoint_sha256': sha256(entrypoint_bytes),
        'publish_order': ['_releases/', 'index.html'],
        'published': False,
        'rollback': 'Retain the previous complete bundle; restore only its root index.html after verifying its assets remain present.',
    }
    (output / 'deployment.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_release(args.source, args.output)))


if __name__ == '__main__':
    main()
