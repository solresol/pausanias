from pathlib import Path
import json

from manto_atlas.build import (
    build_comparisons, containment, figure_profiles, prepare_payload,
    weighted_jaccard, write_site,
)


def test_similarity_empty_is_unknown_not_distinctive():
    assert weighted_jaccard([], ['a'], {}) is None
    assert weighted_jaccard([], [], {}) is None
    assert weighted_jaccard(['a'], ['a'], {'a': 4}) == 1
    assert weighted_jaccard(['a'], ['b'], {}) == 0
    assert weighted_jaccard(['a'], ['a', 'b'], {'a': 2, 'b': 1}) == 2/3


def test_containment_is_asymmetric():
    assert containment(['a'], ['a', 'b'], {}) == 1
    assert containment(['a', 'b'], ['a'], {}) == 0.5
    assert containment([], ['a'], {}) is None


def test_figure_profile_deduplicates_and_rejects_bibliography():
    place = {'p': {}}
    row = dict(source_manto_id='p', target_manto_id='f', relation_type='founded_by',
               source_name='🌍 Place', target_name='👤 Hero')
    profiles, figures, actions = figure_profiles([row, row, {**row, 'relation_type': 'source_attributes'},
        {**row, 'target_name': '📖 Author'}], place)
    assert profiles['p'] == {'f'}
    assert figures == {'f': 'Hero'}
    assert actions['p']['foundation'] == {'f'}


def test_geographic_neighbours_do_not_require_story_overlap():
    places = {'a': {'id':'a','lat':38.,'lon':23.},'b':{'id':'b','lat':38.1,'lon':23.},
              'c':{'id':'c','lat':None,'lon':None},'d':{'id':'d','lat':41.,'lon':23.}}
    pairs, _ = build_comparisons(places, {'a': {'hero'}, 'd': {'hero'}})
    assert len(pairs) == 1
    assert pairs[0]['a'] == 'a' and pairs[0]['b'] == 'b'
    assert pairs[0]['similarity'] is None
    assert 10 < pairs[0]['km'] < 12


def test_claim_candidates_never_become_verified_labels():
    payload = prepare_payload({'record_id':1},[],[],[{'id':1,'canonical_place_name':'Aegae'}],
        [{'english_transcription':'Aegae','reference_form':'Αἰγαί','manto_id':'a'},
         {'english_transcription':'Aegae','reference_form':'Αἰγαί','manto_id':'b'}],[])
    assert payload['claims'][0]['candidate_manto_ids'] == ['a','b']
    assert payload['claims'][0]['review_status'] == 'automated_unreviewed'
    assert 'target_label' not in payload['claims'][0]


def test_release_freshness_matches_the_actual_snapshot():
    from manto_atlas.build import LATEST_PUBLIC
    old = prepare_payload({'record_id':22239985},[],[],[],[],[])
    latest = prepare_payload({'record_id':LATEST_PUBLIC['record_id']},[],[],[],[],[])
    assert old['provenance']['is_latest_verified_public_release'] is False
    assert latest['provenance']['is_latest_verified_public_release'] is True


def test_write_site_has_no_inline_data_injection(tmp_path):
    payload={'release':{'record_id':1},'danger':'</script><script>alert(1)</script>'}
    manifest=write_site(payload,tmp_path)
    assert len(manifest['files']) == 5
    assert '</script>' not in (tmp_path/'data.js').read_text()
    assert json.loads((tmp_path/'data.json').read_text()) == payload
    page=(tmp_path/'index.html').read_text()
    assert 'Content-Security-Policy' in page
    assert 'not a terrain or travel-time map' in page
    assert 'No graph neural network has been trained' in page


def test_export_source_never_initializes_or_mutates_schema():
    source=Path('manto_atlas/build.py').read_text()
    assert 'conn.read_only = True' in source
    assert 'SHOW transaction_read_only' in source
    for forbidden in ('initialize_schema(', 'INSERT INTO', 'UPDATE manto_', 'DELETE FROM', 'ALTER TABLE'):
        assert forbidden not in source
