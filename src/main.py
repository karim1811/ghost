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
from modules.reverse_image import run_full_reverse_search, detect_faces_in_image
from modules.whatsmyname import check_whatsmyname
from modules.social_graph import analyze_github_profile, analyze_reddit_user, cross_platform_identities, generate_behavioral_fingerprint
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
    parser.add_argument("--identity", action="store_true",
                        help="Deep identity analysis: behavioral fingerprint, cross-platform")
    parser.add_argument("--export", "-o", choices=["json", "markdown", "md"],
                        default="markdown", help="Export format (default: markdown)")
    parser.add_argument("--category", "-c", help="Filter by category (social, coding, gaming, media, crypto, forum, pro)")
    parser.add_argument("--image", "-i", help="Path to image for reverse search (local file)")
    parser.add_argument("--image-url", help="Public URL of image for reverse search")
    parser.add_argument("--whatsmyname", "-w", action="store_true",
                        help="Use WhatsMyName (700+ sites, most reliable)")
    parser.add_argument("--wm", type=int, default=None,
                        help="Max sites to check with WhatsMyName (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not args.pseudo and not args.email and not args.image and not args.image_url:
        banner()
        parser.print_help()
        print()
        return

    banner()
    start_time = time.time()

    all_results = []

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

        all_results.extend(results)

    if args.whatsmyname:
        target = args.pseudo or args.email
        if target:
            print(f"\n\n[*] WhatsMyName — checking {target} across 700+ sites...")
            wmn_results = check_whatsmyname(target, max_sites=args.wm)
            wmn_found = [r for r in wmn_results if r.get("exists")]

            # Convert to standard format
            for r in wmn_results:
                r["platform"] = f"WhatsMyName | {r.get('name', '?')}"
                r["url"] = r.get("url", "")

            all_results.extend(wmn_results)
            print(f"  WhatsMyName: {len(wmn_found)}/{len(wmn_results)} sites matched")

            if wmn_found:
                print("\n  🎯 WHATSMYNAME MATCHES:")
                for r in wmn_found[:20]:
                    print(f"  • [{r.get('category', '?')}] {r.get('name')}: {r.get('url')}")
                if len(wmn_found) > 20:
                    print(f"  ... and {len(wmn_found) - 20} more")

    if args.identity and args.pseudo:
        print(f"\n\n[*] Deep Identity Analysis for `{args.pseudo}`...")
        print(f"{'='*60}")

        # GitHub deep
        print("\n  [+] GitHub deep analysis...")
        gh = analyze_github_profile(args.pseudo)
        if gh.get("data"):
            d = gh["data"]
            print(f"      Name: {d.get('name', '?')}")
            print(f"      Bio: {d.get('bio', '?')}")
            print(f"      Location: {d.get('location', '?')}")
            print(f"      Company: {d.get('company', '?')}")
            print(f"      Email: {d.get('email', '?')}")
            print(f"      Twitter: {d.get('twitter', '?')}")
            print(f"      Blog: {d.get('blog', '?')}")
            print(f"      Languages: {list(d.get('top_languages', {}).keys())}")
            print(f"      Timezone (from activity): {d.get('likely_timezone', '?')}")
            if d.get("emails_from_commits"):
                print(f"      Emails from commits: {d['emails_from_commits']}")
        all_results.append(gh)

        # Reddit deep
        print("\n  [+] Reddit deep analysis...")
        rd = analyze_reddit_user(args.pseudo)
        if rd.get("data"):
            d = rd["data"]
            print(f"      Karma: {d.get('total_karma', '?')}")
            print(f"      Verified email: {d.get('has_verified_email', '?')}")
            print(f"      Top subreddits: {dict(list(d.get('active_subreddits', {}).items())[:5])}")
        all_results.append(rd)

        # Cross-platform
        print("\n  [+] Cross-platform identity...")
        cross = cross_platform_identities(args.pseudo)
        for identity in cross.get("identities", []):
            src = identity.get("source", "?")
            print(f"      Identity from {src}:")
            for k, v in identity.items():
                if k != "source":
                    print(f"        {k}: {v}")
        all_results.append(cross)

        # Behavioral fingerprint
        fingerprint = generate_behavioral_fingerprint([gh, rd])
        print(f"\n  🎯 BEHAVIORAL FINGERPRINT:")
        if fingerprint["names"]:
            print(f"      Names: {[n['value'] for n in fingerprint['names']]}")
        if fingerprint["emails"]:
            print(f"      Emails: {[e['value'] for e in fingerprint['emails']]}")
        if fingerprint["locations"]:
            print(f"      Locations: {[l['value'] for l in fingerprint['locations']]}")
        if fingerprint["languages"]:
            print(f"      Languages: {fingerprint['languages']}")
        if fingerprint["connected_accounts"]:
            print(f"      Connected: {fingerprint['connected_accounts']}")
        all_results.append({"platform": "Behavioral Fingerprint", "data": fingerprint, "exists": True, "url": ""})

    # Console summary
        found = [r for r in results if r.get("exists")]
        print(f"\n{'='*60}")
        print(f"  GHOST RESULTS for `{args.pseudo}`")
        print(f"{'='*60}")
        print(f"  Profiles found: {len(found)}/{len(results)}")
        print(f"  Time: {time.time() - start_time:.1f}s")
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

        all_results.extend([grav, psb])

    if args.image or args.image_url:
        print(f"\n\n[*] Reverse Image Search")
        print(f"{'='*60}")

        report = run_full_reverse_search(
            image_path=args.image,
            image_url=args.image_url
        )

        report["platform"] = "Reverse Image Search"
        report["exists"] = True
        report["url"] = args.image or args.image_url

        # Print results
        if args.image:
            face = report.get("face_detection", {})
            print(f"\n  Image: {args.image}")
            print(f"  Face detected (heuristic): {face.get('has_face', 'N/A')}")
            print(f"  Confidence: {face.get('confidence', 0)}%")
            if face.get("note"):
                print(f"  Note: {face['note']}")

        print("\n  🔍 SEARCH URLS (copy to browser):")
        search_urls = report.get("search_urls", {})

        if not search_urls:
            # Try building from local
            if args.image and os.path.exists(args.image):
                search_urls = {
                    "yandex": f"https://yandex.com/images/search?rpt=imageview",
                    "google_lens": "https://lens.google.com/",
                    "facecheck": "https://facecheck.id/",
                    "pimeyes": "https://pimeyes.com/en",
                }
                print(f"\n  [!] Local file: use browser to upload image:")
                print(f"      → Yandex: {search_urls['yandex']}")
                print(f"      → Google Lens: {search_urls['google_lens']}")
                print(f"      → Facecheck.id: {search_urls['facecheck']}")
                print(f"      → PimEyes: {search_urls['pimeyes']}")

                # Show face-specific engines
                pimeyes = report.get("pimeyes", {})
                print(f"\n  🎯 FACE SEARCH ENGINES:")
                print(f"      • PimEyes: {pimeyes.get('website')} — {pimeyes.get('free_tier', '')}")

        for engine, url in search_urls.items():
            print(f"  → {engine}: {url}")

        # Show Yandex result if available
        ya = report.get("yandex", {})
        if ya.get("found"):
            print(f"\n  Yandex: {ya.get('matches', [])}")

        all_results.append(report)

    # ── Final report ──
    if not all_results:
        parser.print_help()
        print()
        return

    target = args.pseudo or args.email or (args.image or args.image_url or "target")
    report_path = generate_report(target, all_results, report_type=args.export)
    print(f"\n  📄 Full report: {report_path}")
    print(f"  ⏱ Total time: {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    main()
