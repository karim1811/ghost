#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST — Global Heuristic OSINT Search Tool
# Point d'entrée CLI
# ──────────────────────────────────────────────────────────

import sys
import os
import argparse
import time
from pathlib import Path

# ── Add project root to path ────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# ── Suppress SSL warnings ──────────────────────────────
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from modules.platforms import PLATFORMS, CATEGORIES
from modules.http_utils import head_check, get_check, api_get, polite_request
from modules.specialized import check_github, check_reddit, check_steam, check_hackernews
from modules.leaks import check_gravatar, check_keybase, check_epieos, check_psbdmp
from modules.report import generate_report


def banner():
    print("""
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   OSINT Engine v0.1 | No One Is Invisible
""")


def search_pseudo(username: str, deep: bool = False) -> list:
    """Core function: search pseudo on all platforms"""
    results = []
    total = len(PLATFORMS)
    print(f"\n[*] Scanning {total} plateformes pour `{username}`...\n")

    checked = 0
    for name, info in PLATFORMS.items():
        checked += 1
        url = info["url"].replace("{username}", username)
        ptype = info.get("type", "unknown")

        # Progress bar
        icon = "✓" if checked % 10 == 0 else "·"
        sys.stdout.write(f"\r  [{checked}/{total}] {icon} Checking {name}...")
        sys.stdout.flush()

        # Use specialized checks for supported platforms
        try:
            if name == "github":
                r = check_github(username)
                r["platform"] = name
                r["url"] = url
                results.append(r)
                continue
            elif name == "reddit":
                r = check_reddit(username)
                results.append(r)
                continue
            elif name == "steam":
                r = check_steam(username)
                results.append(r)
                continue
            elif name == "hackernews":
                r = check_hackernews(username)
                results.append(r)
                continue

            # Generic check via HEAD request
            check_result = head_check(url)

            # If ambiguous (None), verify with GET
            if check_result.get("exists") is None:
                check_result = get_check(url)

            # Skip if errored
            if check_result.get("err"):
                continue

            results.append({
                "platform": name,
                "type": ptype,
                "url": url,
                "exists": check_result.get("exists", False) or False,
                "status_code": check_result.get("status_code"),
                "error": check_result.get("error"),
                "title": check_result.get("title", ""),
            })

        except Exception as e:
            results.append({
                "platform": name,
                "type": ptype,
                "url": url,
                "exists": None,
                "error": str(e),
            })

        # Be polite
        if not deep:
            time.sleep(0.15)

    print()
    return results


def deep_search(username: str) -> dict:
    """
    Deep OSINT — extensions + specialized tools
    """
    deep_results = {}

    # Check Keybase (identity proofs)
    print("\n[*] Deep mode: checking identity sources...")
    deep_results["keybase"] = check_keybase(username)

    # Check paste dumps
    deep_results["psbdmp"] = check_psbdmp(username=username)

    # Check Epieos if we have email
    # (would need to run after finding email from other sources)

    return deep_results


def main():
    parser = argparse.ArgumentParser(
        description="GHOST — Global OSINT Search Tool. Reveal anonymous profiles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --pseudo eth.git
  python src/main.py --pseudo eth.git --deep
  python src/main.py --email test@mail.com
  python src/main.py --pseudo eth.git --export json
        """,
    )

    parser.add_argument("--pseudo", "-p", help="Pseudo/username to search")
    parser.add_argument("--email", "-e", help="Email address to search")
    parser.add_argument("--deep", "-d", action="store_true",
                        help="Deep mode: slower but more thorough (Keybase, paste dumps)")
    parser.add_argument("--export", "-o", choices=["json", "markdown", "md"],
                        default="markdown", help="Export format (default: markdown)")
    parser.add_argument("--category", "-c", help="Filter by category (social, coding, gaming, media, crypto, forum, pro)")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not args.pseudo and not args.email:
        banner()
        parser.print_help()
        print()
        return

    banner()
    start_time = time.time()

    if args.pseudo:
        print(f"\n[*] Target pseudo: {args.pseudo}")
        print(f"[*] Mode: {'DEEP' if args.deep else 'STANDARD'}")
        print(f"[*] Export: {args.export}")
        print()

        # Main search
        results = search_pseudo(args.pseudo, deep=args.deep)

        # Deep mode extras
        if args.deep:
            extras = deep_search(args.pseudo)
            for key, val in extras.items():
                val["platform"] = key.capitalize()
                results.append(val)

        # Generate report
        report_path = generate_report(args.pseudo, results, report_type=args.export)

        # Console summary
        found = [r for r in results if r.get("exists")]
        print(f"\n{'='*60}")
        print(f"  GHOST RESULTS for `{args.pseudo}`")
        print(f"{'='*60}")
        print(f"  Profiles found: {len(found)}/{len(results)}")
        print(f"  Time: {time.time() - start_time:.1f}s")
        print(f"  Report: {report_path}")
        print(f"{'='*60}")

        if found:
            print("\n  🎯 FOUND PROFILES:")
            for r in found:
                print(f"  • {r.get('platform', '?')}: {r.get('url', '')}")
                if r.get("data"):
                    for k, v in r["data"].items():
                        if v:
                            print(f"    └ {k}: {v}")
            print()
        else:
            print("\n  ⚠ No profiles found. Try:")
            print("  • Variants (with/without underscores, numbers)")
            print("  • Deep mode --deep for Keybase/pastes")
            print("  • Reverse image search if photo available\n")

    if args.email:
        print(f"\n[*] Target email: {args.email}")

        # Gravatar
        grav = check_gravatar(args.email)
        print(f"\n  Gravatar: {'FOUND' if grav['found'] else 'NOT FOUND'}")
        if grav["found"]:
            print(f"  Profile: {grav.get('profile_url')}")
            print(f"  Data: {grav.get('data')}")

        # Pastdumps
        psb = check_psbdmp(email=args.email)
        print(f"  Paste dumps: {len(psb.get('data', []))} results")


if __name__ == "__main__":
    main()
