import hashlib
import json
from pathlib import Path
import pytest

from manto_atlas.build import write_site
from prepare_epimanto_release import prepare_release, ASSETS


def fixture(tmp_path):
    source = tmp_path / 'source'
    write_site({'schema_version': 1, 'release': {'record_id': 23079055}}, source)
    return source, tmp_path / 'bundle'


def test_local_bundle_is_pinned_and_entrypoint_switches_all_assets(tmp_path):
    source, output = fixture(tmp_path)
    result = prepare_release(source, output)
    assert result['published'] is False
    assert result['publish_order'] == ['_releases/', 'index.html']
    prefix = result['asset_prefix']
    for name in ASSETS | {'manifest.json'}:
        assert (output / prefix / name).read_bytes() == (source / name).read_bytes()
    root = (output / 'index.html').read_text()
    for name in ['app.js', 'data.js', 'style.css', 'data.json', 'manifest.json']:
        assert '="' + prefix + name + '"' in root
        assert '="' + name + '"' not in root
    assert 'content="' + result['release_name'] + '"' in root
    assert hashlib.sha256((output/'index.html').read_bytes()).hexdigest() == result['entrypoint_sha256']
    # Source remains an independently usable, unmodified local preview.
    assert 'src="data.js"' in (source/'index.html').read_text()


def test_unchanged_sources_have_same_immutable_release_name(tmp_path):
    source, output = fixture(tmp_path)
    a = prepare_release(source, output)
    b = prepare_release(source, tmp_path/'other')
    assert a['release_name'] == b['release_name']


def test_existing_bundle_is_never_overwritten(tmp_path):
    source, output = fixture(tmp_path)
    output.mkdir()
    (output/'keep.txt').write_text('unrelated')
    with pytest.raises(ValueError, match='already exists'):
        prepare_release(source, output)
    assert (output/'keep.txt').read_text() == 'unrelated'


def test_changed_asset_fails_before_any_output(tmp_path):
    source, output = fixture(tmp_path)
    (source/'app.js').write_text('changed')
    with pytest.raises(ValueError, match='Checksum mismatch'):
        prepare_release(source, output)
    assert not output.exists()


def test_symlinked_asset_is_rejected(tmp_path):
    source, output = fixture(tmp_path)
    (source/'style.css').rename(tmp_path/'style.css')
    (source/'style.css').symlink_to(tmp_path/'style.css')
    with pytest.raises(ValueError, match='symlinked'):
        prepare_release(source, output)
    assert not output.exists()


def test_manifest_cannot_request_unrelated_files(tmp_path):
    source, output = fixture(tmp_path)
    manifest = json.loads((source/'manifest.json').read_text())
    manifest['files']['../../secret'] = '0'*64
    (source/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='unsafe source manifest'):
        prepare_release(source, output)
    assert not output.exists()


def test_snapshot_identity_must_match_manifest(tmp_path):
    source, output = fixture(tmp_path)
    manifest = json.loads((source/'manifest.json').read_text())
    manifest['release_record_id'] = 1
    (source/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='release IDs disagree'):
        prepare_release(source, output)
    assert not output.exists()
