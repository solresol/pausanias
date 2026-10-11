import json
import runpy
from pathlib import Path

import pytest
import requests


SCRIPT = Path(__file__).resolve().parents[1] / "scraper.py"


class Response:
    def __init__(self, text="", data=None, status_code=200):
        self.text = text
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data


class Session:
    def __init__(self, login_ok=True):
        self.headers = {}
        self.cookies = requests.cookies.cookiejar_from_dict(
            {"PHPSESSID": "fixture-session"} if login_ok else {}
        )
        self.login_ok = login_ok
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url.endswith("/login"):
            return Response(text='<input name="csrf_token" value="fixture-csrf">')
        if "/types/all/list/" in url:
            return Response(text='<a href="type-7">Source</a><a href="type-8">Place</a>')
        if url.endswith("/type/7/object/41"):
            return Response(data={"object_id": 41, "title": "Pausanias"})
        if url.endswith("/type/8/object/61"):
            return Response(data={"object_id": 61, "source": 41})
        raise AssertionError(f"Unexpected request: {url}")

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/login"):
            return Response(status_code=302 if self.login_ok else 200)
        if url.endswith("/type/7/query"):
            return Response(data=[{"object_id": 41}])
        if url.endswith("/type/8/query"):
            return Response(data=[{"object_id": 61}])
        raise AssertionError(f"Unexpected request: {url}")


@pytest.fixture
def configure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MANTO_USER", "fixture-user")
    monkeypatch.setenv("MANTO_PASS", "fixture-password-never-logged")
    monkeypatch.setattr("time.sleep", lambda _: None)
    return tmp_path


def test_scraper_preserves_exports_without_logging_credentials(configure, monkeypatch, capsys):
    session = Session()
    monkeypatch.setattr(requests, "Session", lambda: session)
    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert json.loads((configure / "pausanias_sources.json").read_text()) == {
        "41": {"object_id": 41, "title": "Pausanias"}
    }
    assert json.loads((configure / "pausanias_objects.json").read_text()) == {
        "Place": {"61": {"object_id": 61, "source": 41}}
    }
    login = next(call for call in session.calls if call[0] == "POST" and call[1].endswith("/login"))
    assert login[2]["data"]["csrf_token"] == "fixture-csrf"
    assert login[2]["data"]["login_user"] == "fixture-user"
    assert login[2]["data"]["login_ww"] == "fixture-password-never-logged"
    output = capsys.readouterr().out
    assert "fixture-password-never-logged" not in output
    assert "fixture-user" not in output
    assert "fixture-csrf" not in output


def test_failed_login_stops_before_queries_or_exports(configure, monkeypatch):
    session = Session(login_ok=False)
    monkeypatch.setattr(requests, "Session", lambda: session)
    with pytest.raises(SystemExit, match="login failed"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert len(session.calls) == 2
    assert not (configure / "pausanias_sources.json").exists()
    assert not (configure / "pausanias_objects.json").exists()
