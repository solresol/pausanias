#!/usr/bin/env python3
"""
Scrape everything in MANTO whose Source mentions ‘Pausanias’
without using the public Data-API.  Requires only a normal
username/password (no admin rights).
"""

import getpass
import json
import os
import pathlib
import re
import time

import requests
from bs4 import BeautifulSoup

BASE      = "https://manto.unh.edu"
PROJ_ID   = 60
RATE_S    = 0.6
OUTDIR    = pathlib.Path(".")

# ────────────────────────────────────────────────────────────
# 1. log in and keep the PHP session cookie
# ────────────────────────────────────────────────────────────
user = os.getenv("MANTO_USER") or input("Username: ")
pw   = os.getenv("MANTO_PASS") or getpass.getpass("Password: ")

s = requests.Session()
s.headers["User-Agent"] = "manto-ui-scraper/1.0 (+github.com/you)"

# pull the login page once to pick up CSRF token & form action
login_html = s.get(f"{BASE}/login").text
soup       = BeautifulSoup(login_html, "html.parser")

payload = {
    "login_user":     user,
    "login_ww": pw,
}


csrf = soup.find("input", {"name": "csrf_token"})
if csrf is not None:
    payload["csrf_token"] = csrf["value"]   # optional – add only if present
r = s.post(f"{BASE}/login", data=payload, allow_redirects=False)
if r.status_code != 302 or "PHPSESSID" not in s.cookies.get_dict():
    raise SystemExit("☠️  login failed – check credentials")

print("✓ logged in")

# ────────────────────────────────────────────────────────────
# 2. find the numeric type-id for ‘Source’
# ────────────────────────────────────────────────────────────
types_html = s.get(f"{BASE}/viewer.p/{PROJ_ID}/2800/types/all/list/").text
type_ids   = {                              # map name → id as we spot them
    m.group(2): int(m.group(1))
    for m in re.finditer(r'type-(\d+)".*?>([^<]+)</a>', types_html)
}
if "Source" not in type_ids:
    raise SystemExit("Couldn’t locate a type literally called “Source”")

SRC_ID = type_ids["Source"]
print(f"Source type id = {SRC_ID}")

# ────────────────────────────────────────────────────────────
# 3. search that type for “Pausanias”
# ────────────────────────────────────────────────────────────
q = {
    "search": "Pausanias",
    "limit":  10000,
}
src_list = s.post(
    f"{BASE}/ui_data/project/{PROJ_ID}/type/{SRC_ID}/query",
    data=q, timeout=30
).json()

src_ids = [row["object_id"] for row in src_list]
print(f"Found {len(src_ids)} Source objects mentioning Pausanias")

# dump the full Source objects
sources = {}
for oid in src_ids:
    j = s.get(
        f"{BASE}/ui_data/project/{PROJ_ID}/type/{SRC_ID}/object/{oid}",
        timeout=30
    ).json()
    sources[oid] = j
    time.sleep(RATE_S)

# ────────────────────────────────────────────────────────────
# 4. iterate over *all* other types and pull objects that cite them
# ────────────────────────────────────────────────────────────
results = {}
for name, tid in type_ids.items():
    if tid == SRC_ID:
        continue

    filt = {"sources": ",".join(map(str, src_ids))}
    r = s.post(
        f"{BASE}/ui_data/project/{PROJ_ID}/type/{tid}/query",
        data=filt, timeout=30
    ).json()

    if not r:
        continue

    print(f"{name:<25} {len(r):>5}")
    objs = {}
    for row in r:
        oid = row["object_id"]
        obj = s.get(
            f"{BASE}/ui_data/project/{PROJ_ID}/type/{tid}/object/{oid}",
            timeout=30
        ).json()
        objs[oid] = obj
        time.sleep(RATE_S)
    results[name] = objs

# ────────────────────────────────────────────────────────────
# 5. write everything to disk
# ────────────────────────────────────────────────────────────
(OUTDIR / "pausanias_sources.json").write_text(
    json.dumps(sources, indent=2, ensure_ascii=False)
)
(OUTDIR / "pausanias_objects.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False)
)

print("✨ done – files written next to the script")
