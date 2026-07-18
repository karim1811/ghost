#!/usr/bin/env python3
"""Prove real WMN detection works on a non-anti-bot site (GitHub) + fake negative."""
import sys, importlib.util, types, httpx
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

data = load_wmn_data()
d = {s["name"]: s for s in data["sites"]}
gh = d.get("GitHub (User)")
h = get_headers(); h["Accept"] = "application/json, text/html"
for acc, label in [("torvalds", "REAL"), ("nope_no_such_user_xyz987", "FAKE")]:
    uri = gh["uri_check"].replace("{account}", acc)
    r = httpx.get(uri, headers=h, follow_redirects=True, verify=False, timeout=15)
    ok, reason = determine_existence(r, gh)
    print(f"[{label}] GitHub/{acc} -> detected={ok} ({reason}, HTTP {r.status_code})")
