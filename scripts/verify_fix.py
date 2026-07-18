#!/usr/bin/env python3
"""
Compare OLD vs NEW WhatsMyName existence logic on a real account.
- OLD: exists if e_string present, OR (m_string absent)  -> false positives
- NEW: determine_existence() with code+string gating      -> correct
We scan a subset of sites and report how many "found" each yields, plus a
manual spot-check of whether the reported URLs are real profiles.
"""
import sys, importlib.util, types, json, time
from pathlib import Path

MODS = Path(__file__).resolve().parent.parent / "src" / "modules"
sys.path.insert(0, str(MODS))

# Load whatsmyname + deps as a package (relative imports)
pkg = types.ModuleType("ghostmods")
pkg.__path__ = [str(MODS)]
sys.modules["ghostmods"] = pkg
for dep in ("http_utils", "detection_patterns"):
    spec = importlib.util.spec_from_file_location(f"ghostmods.{dep}", str(MODS / f"{dep}.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[f"ghostmods.{dep}"] = m
    spec.loader.exec_module(m)
spec = importlib.util.spec_from_file_location("ghostmods.whatsmyname", str(MODS / "whatsmyname.py"))
wmn = importlib.util.module_from_spec(spec)
sys.modules["ghostmods.whatsmyname"] = wmn
spec.loader.exec_module(wmn)

import httpx
from ghostmods.http_utils import get_headers

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "noyeurdeboutgnole"
MAX_SITES = int(sys.argv[2]) if len(sys.argv) > 2 else 60

data = wmn.load_wmn_data()
all_sites = [s for s in data["sites"] if "cloudflare" not in s.get("protection", [])]
# focus on known big socials for a meaningful spot-check (search whole dataset)
focus_names = ("Instagram", "GitHub", "Twitter", "Reddit", "TikTok", "YouTube",
               "LinkedIn", "Pinterest", "Steam", "Twitch", "Facebook", "VK")
focus = [s for s in all_sites if s.get("name") in focus_names]
# also add a sample of other sites (capped) for false-positive measurement
others = [s for s in all_sites if s.get("name") not in focus_names][:MAX_SITES]
sites = focus + others

def old_exists(r, site):
    e = site.get("e_string", "") or ""
    m = site.get("m_string", "") or ""
    if e and e in r.text:
        return True
    if m and m not in r.text:
        return True
    return False

headers = get_headers(); headers["Accept"] = "text/html"
old_found, new_found = [], []
with httpx.Client(timeout=10, headers=headers, follow_redirects=True, verify=False) as client:
    for site in focus:
        uri = site.get("uri_check", "").replace("{account}", USERNAME)
        if not uri:
            continue
        try:
            r = client.get(uri)
        except Exception as e:
            continue
        time.sleep(0.1)
        o = old_exists(r, site)
        n, reason = wmn.determine_existence(r, site)
        if o:
            old_found.append((site["name"], uri, r.status_code))
        if n:
            new_found.append((site["name"], uri, reason, r.status_code))

print(f"=== Username: {USERNAME} (focus subset, {len(focus)} sites) ===")
print(f"OLD logic reported FOUND: {len(old_found)}")
print(f"NEW logic reported FOUND: {len(new_found)}")
print("\n-- NEW found (these should be REAL, clickable profiles) --")
for name, uri, reason, code in new_found:
    print(f"  [{name}] {uri}  ({reason}, HTTP {code})")
print("\n-- OLD-only false positives (reported by OLD, rejected by NEW) --")
old_only = [x for x in old_found if x[0] not in {y[0] for y in new_found}]
for name, uri, code in old_only:
    print(f"  [{name}] {uri}  (HTTP {code})")
