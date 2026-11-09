import hashlib
import zipfile
from types import SimpleNamespace
import pytest

from manto_stage_import import create_stage, inspect_archive, validate_schema_name, validate_endpoint, TABLES
from manto_importer import ENTITY_DETAILS_PATH, TIE_DETAILS_PATH


def test_stage_names_cannot_target_public_or_inject_sql():
    assert validate_schema_name('manto_stage_23079055_20261109')
    for name in ['public','public, pg_catalog','manto_stage_foo; DROP SCHEMA public','manto_stage_','manto_stage_'+'x'*46]:
        with pytest.raises(ValueError):
            validate_schema_name(name)
    assert len(TABLES)==7


def test_endpoint_guard_rejects_wrong_host_role_port_database_or_major():
    good=dict(server_version=180006,dbname='pausanias',port=5433,host='/var/run/postgresql',user='gregb')
    validate_endpoint(SimpleNamespace(**good))
    for key,value in [('server_version',160015),('dbname','other'),('port',5432),('host','remote'),('user','other')]:
        with pytest.raises(RuntimeError):
            validate_endpoint(SimpleNamespace(**{**good,key:value}))


def test_stage_uses_session_search_path_without_public_fallback():
    class FakeConnection:
        def __init__(self):
            self.queries=[]
            self.commits=0
        def execute(self,query,params=None):
            text=query if isinstance(query,str) else query.as_string()
            self.queries.append(text)
            value=None if 'to_regnamespace' in text else 'manto_stage_test'
            return SimpleNamespace(fetchone=lambda:(value,))
        def commit(self):
            self.commits+=1
    conn=FakeConnection()
    create_stage(conn,'manto_stage_test')
    assert 'SET search_path TO "manto_stage_test"' in conn.queries
    assert not any('SET LOCAL search_path' in q or 'GRANT ' in q for q in conn.queries)
    assert sum(q.startswith('CREATE TABLE') for q in conn.queries)==7
    assert sum('ADD FOREIGN KEY' in q for q in conn.queries)==7


def make_archive(tmp_path):
    p=tmp_path/'release.zip'
    with zipfile.ZipFile(p,'w') as z:
        for name in [ENTITY_DETAILS_PATH,TIE_DETAILS_PATH]:
            z.writestr(name,'"nodegoat ID","Object ID",Name\nnode,1,🌍 Athens\n')
    r=SimpleNamespace(file_size=p.stat().st_size,file_checksum='md5:'+hashlib.md5(p.read_bytes()).hexdigest())
    return p,r


def test_archive_checks_identity_shape_and_counts(tmp_path):
    p,r=make_archive(tmp_path)
    result=inspect_archive(p,r)
    assert result['zip_entries']==2
    assert result['detail_csv_rows']=={ENTITY_DETAILS_PATH:1,TIE_DETAILS_PATH:1}


def test_archive_rejects_wrong_checksum_or_byte_size(tmp_path):
    p,r=make_archive(tmp_path)
    r.file_checksum=''
    with pytest.raises(ValueError,match='checksum'):
        inspect_archive(p,r)
    r.file_checksum='md5:'+hashlib.md5(p.read_bytes()).hexdigest()
    r.file_size+=1
    with pytest.raises(ValueError,match='byte-size'):
        inspect_archive(p,r)
