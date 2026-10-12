#!/usr/bin/env python3
"""Publish the report-integrity one-pager to GitHub Pages. Never prints the token."""
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.request

HOME = pathlib.Path(os.environ["HOME"])
SRC = pathlib.Path("/root/.hermes/profiles/banksy/outputs/ib-report-integrity")
REPO = "ib-report-integrity"

cred = (HOME / ".git-credentials").read_text().strip()
match = re.search(r"x-access-token:([^@]+)@github\.com", cred)
if not match:
    raise SystemExit("no token in the git credential store")
TOKEN = match.group(1)
login = re.search(r"https://([^:]+):", cred)
print("credential found for:", login.group(1) if login else "(unknown)")
print("token length:", len(TOKEN), "chars (value never printed)")


def api(path, payload=None, method=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "banksy-agent",
            "Content-Type": "application/json",
        },
        method=method or ("POST" if payload is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


status, me = api("/user")
owner = me.get("login")
print(f"account: {owner} (api {status})")

status, repo = api("/user/repos", {"name": REPO, "private": False, "auto_init": False})
print(f"repo create: {status}", repo.get("full_name") or repo.get("message"))

# the repo content: the page, the PDF and the QR only
(SRC / ".gitignore").write_text("page1.png\npreview.png\nbuild.py\n")

env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=SRC, env=env, capture_output=True, text=True, check=check)

if not (SRC / ".git").exists():
    git("init", "-b", "main")
git("add", "-A")
git("config", "user.email", "agent@banksy.local")
git("config", "user.name", "Banksy (agent)")
git("commit", "-q", "-m", "instructBrain report integrity, October 2026 (IB-RPT-001)")
git("remote", "remove", "origin", check=False)
git("remote", "add", "origin", f"https://github.com/{owner}/{REPO}.git")
push = git("push", "-u", "origin", "main", check=False)
print("push:", (push.stdout + push.stderr).strip().splitlines()[-1][:120])

status, pages = api(f"/repos/{owner}/{REPO}/pages", {"source": {"branch": "main", "path": "/"}})
if status == 409:
    status, pages = api(f"/repos/{owner}/{REPO}/pages", {"source": {"branch": "main", "path": "/"}}, method="PUT")
print(f"pages enable: {status}", pages.get("html_url") or pages.get("message"))

URL = f"https://{owner}.github.io/{REPO}/"
print("waiting for Pages to serve", URL)
ok = False
for i in range(24):
    time.sleep(10)
    try:
        with urllib.request.urlopen(URL, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            code = r.status
    except Exception as exc:
        print(f"  {i*10+10}s: not yet ({exc})")
        continue
    if code == 200 and "IB-RPT-001" in body:
        print(f"  {i*10+10}s: LIVE (200, marker present, {len(body)} bytes)")
        ok = True
        break
    print(f"  {i*10+10}s: 200 but no marker yet")

pdf_url = URL + "IB-RPT-001.pdf"
try:
    req = urllib.request.Request(pdf_url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"pdf: {r.status} {r.headers.get('content-type')} {r.headers.get('content-length')} bytes")
except Exception as exc:
    print("pdf:", exc)

print()
print("PAGE:", URL)
print("PDF :", pdf_url)
print("LIVE:", ok)
