#!/usr/bin/env python3
"""Fast local test: prove real detection + dossier gen/scoring (no 700-site scan)."""
import sys, importlib.util, types, re, httpx
from pathlib import Path

MODS = Path(__file__).resolve().parent.parent / "src" / "modules"
sys.path.insert(0, str(MODS))
pkg = types.ModuleType("ghostmods"); pkg.__path__ = [str(MODS)]
sys.modules["ghostmods"] = pkg
for dep in ("http_utils", "detection_patterns"):
    s = importlib.util.spec_from_file_location(f"ghostmods.{dep}", str(MODS / f"{dep}.py"))
    m = importlib.util.module_from_spec(s); sys.modules[f"ghostmods.{dep}"] = m; s.loader.exec_module(m)
from ghostmods.whatsmyname import determine_existence, load_wmn_data
from ghostmods.http_utils import get_headers
from ghostmods.dossier import generate_dossier

USERNAME = "noyeurdeboutgnole"
SOURCE_URL = "https://www.instagram.com/noyeurdeboutgnole/"
data = load_wmn_data()
site_def = {s["name"]: s for s in data["sites"]}

# 1) Prove REAL detection: 'cristiano' Instagram should be detected
insta = site_def.get("Instagram")
uri = insta["uri_check"].replace("{account}", "cristiano")
h = get_headers(); h["Accept"] = "text/html"
r = httpx.get(uri, headers=h, follow_redirects=True, verify=False, timeout=15)
ok, reason = determine_existence(r, insta)
print(f"[*] REAL account 'cristiano' Instagram -> detected={ok} ({reason}, HTTP {r.status_code})")

# 2) Prove NO false positive on a guaranteed-missing account
uri2 = insta["uri_check"].replace("{account}", "this_username_does_not_exist_xyz123")
r2 = httpx.get(uri2, headers=h, follow_redirects=True, verify=False, timeout=15)
ok2, reason2 = determine_existence(r2, insta)
print(f"[*] FAKE account Instagram -> detected={ok2} ({reason2}, HTTP {r2.status_code})")

# 3) Dossier generation for noyeurdeboutgnole with pasted link
additional = [{"site": "Pasted Profile", "url": SOURCE_URL,
               "category": "Confirmed source", "confirmed": True}]
adv = {"photos": [], "personal_info": {}, "google_dorks": {"findings": []}, "wayback": {"snapshots": []}}
html = generate_dossier(USERNAME, [], adv, additional, source_url=SOURCE_URL)
score = re.search(r"ANONYMITY SCORE:\s*(\d+)/100", html)
print(f"\n[+] Score (pasted link only): {score.group(1) if score else '?'}")
print(f"[+] Source link in HTML: {'YES' if SOURCE_URL in html else 'NO'}")
print(f"[+] NOT ANONYMOUS verdict: {'NOT ANONYMOUS' in html}")
print(f"[+] Anti-bot note: {'anti-bot' in html.lower()}")
print(f"[+] HTML length: {len(html)} chars")
