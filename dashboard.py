#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
# GHOST Dashboard — Streamlit Web Interface
# Visualisation des rapports OSINT + lancement de scans
# ──────────────────────────────────────────────────────────
#
# Usage:
#   streamlit run dashboard.py
#
# Déploiement:
#   → Streamlit Cloud (gratuit): https://streamlit.io/cloud
#   → Railway / Render (voir README)
# ──────────────────────────────────────────────────────────

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Config ──────────────────────────────────────────────
ROOT = Path(__file__).parent
REPORTS_DIR = ROOT / "src" / "reports"
PENDING_DIR = ROOT / "pending"
SRC_DIR = ROOT / "src"

# ── Page Config ─────────────────────────────────────────
st.set_page_config(
    page_title="👻 GHOST Dashboard",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff4b4b;
    }
    .stat-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #333;
    }
    .found-badge {
        background: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .not-found-badge {
        background: #333;
        color: #888;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .report-box {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #333;
        max-height: 600px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="main-header">👻 GHOST</p>', unsafe_allow_html=True)
    st.caption("OSINT Engine v0.2")
    st.markdown("---")

    page = st.radio("Navigation", [
        "🏠 Home",
        "🔍 New Scan",
        "📊 Reports",
        "📁 History",
        "⚙️ Settings"
    ])

    st.markdown("---")
    st.caption("Status")
    enrich_status = "🟢 Ready" if (ROOT / "ghost-enrich-server.py").exists() else "🔴 Server not found"
    st.text(f"Enrichment: {enrich_status}")

# ── Functions ───────────────────────────────────────────

def get_reports():
    """Liste tous les rapports générés"""
    if not REPORTS_DIR.exists():
        return []
    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports

def parse_report_metadata(filepath):
    """Extrait les métadonnées d'un rapport"""
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")

        target = "?"
        found = 0
        total = 0
        enriched = "Enriched" in content

        for line in lines[:10]:
            if "Target:" in line:
                target = line.split("`")[1] if "`" in line else "?"
            if "profiles found" in line.lower() or "Scan:" in line:
                parts = line.split("/")
                if len(parts) == 2:
                    try:
                        found = int(parts[0].split()[-1].strip("| "))
                        total = int(parts[1].split()[0].strip("|: "))
                    except (ValueError, IndexError):
                        pass

        return {
            "target": target,
            "found": found,
            "total": total,
            "enriched": enriched,
            "date": datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "path": str(filepath),
            "size": filepath.stat().st_size,
        }
    except Exception:
        return None

def run_scan(target, deep=False, enrich=False, export_format="markdown"):
    """Lance un scan GHOST"""
    cmd = [sys.executable, str(SRC_DIR / "main.py"), "--pseudo", target, "--export", export_format]
    if deep:
        cmd.append("--deep")
    if enrich:
        cmd.append("--enrich")

    env = os.environ.copy()
    env["GHOST_ENRICH_MODE"] = "file"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(ROOT),
        env=env,
    )
    return result

# ── Pages ───────────────────────────────────────────────

def page_home():
    """Page d'accueil avec stats"""
    st.markdown('<p class="main-header">👻 GHOST Dashboard</p>', unsafe_allow_html=True)
    st.caption("AI-Powered OSINT Engine — No One Is Invisible")

    # Stats
    reports = get_reports()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Scans", len(reports))
    with col2:
        enriched = sum(1 for r in reports if parse_report_metadata(r) and parse_report_metadata(r)["enriched"])
        st.metric("AI Enriched", enriched)
    with col3:
        targets = len(set(parse_report_metadata(r)["target"] for r in reports if parse_report_metadata(r)))
        st.metric("Unique Targets", targets)
    with col4:
        pending = len(list(PENDING_DIR.glob("*.json"))) if PENDING_DIR.exists() else 0
        st.metric("Pending", pending)

    st.markdown("---")

    # Recent reports
    st.subheader("Recent Reports")
    if reports:
        for r in reports[:5]:
            meta = parse_report_metadata(r)
            if meta:
                with st.expander(f"**{meta['target']}** — {meta['date']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Found", f"{meta['found']}/{meta['total']}")
                    col2.metric("Enriched", "✅" if meta['enriched'] else "❌")
                    col3.metric("Size", f"{meta['size']//1024}KB")
                    if st.button("View Report", key=f"view_{r.name}"):
                        st.session_state["view_report"] = str(r)
                        st.rerun()
    else:
        st.info("No reports yet. Go to 'New Scan' to start.")


def page_new_scan():
    """Page pour lancer un nouveau scan"""
    st.markdown('<p class="main-header">🔍 New Scan</p>', unsafe_allow_html=True)

    with st.form("scan_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            target = st.text_input("Target (username or email)", placeholder="username or email@domain.com")
        with col2:
            scan_type = st.selectbox("Type", ["Username", "Email"])

        col1, col2, col3 = st.columns(3)
        with col1:
            deep = st.checkbox("Deep mode (Keybase, pastes)")
        with col2:
            enrich = st.checkbox("AI Enrichment", value=True)
        with col3:
            export_format = st.selectbox("Export", ["markdown", "json"])

        submitted = st.form_submit_button("🚀 Launch Scan", use_container_width=True)

    if submitted and target:
        with st.spinner(f"Scanning {target}..."):
            progress = st.progress(0)
            status = st.empty()

            status.text("Phase 1/2: Scanning platforms...")
            progress.progress(30)

            result = run_scan(
                target,
                deep=deep,
                enrich=enrich,
                export_format=export_format,
            )

            progress.progress(80)
            status.text("Phase 2: Generating report...")

            if result.returncode == 0:
                progress.progress(100)
                status.text("✅ Scan complete!")

                # Afficher un résumé
                output = result.stdout
                st.success("Scan completed!")

                # Extraire le chemin du rapport
                for line in output.split("\n"):
                    if "Full report:" in line:
                        report_path = line.split("Full report:")[1].strip()
                        st.session_state["view_report"] = report_path
                        break

                with st.expander("Raw Output", expanded=False):
                    st.code(output)
            else:
                progress.progress(100)
                status.text("❌ Scan failed!")
                st.error("Scan failed. Check output below.")
                st.code(result.stderr if result.stderr else result.stdout)

    elif submitted:
        st.warning("Please enter a target.")


def page_reports():
    """Page pour voir les rapports"""
    st.markdown('<p class="main-header">📊 Reports</p>', unsafe_allow_html=True)

    reports = get_reports()
    if not reports:
        st.info("No reports yet.")
        return

    # Sélecteur de rapport
    report_names = [f"{parse_report_metadata(r)['target']} — {parse_report_metadata(r)['date']}" for r in reports if parse_report_metadata(r)]
    selected = st.selectbox("Select Report", report_names)

    if selected:
        idx = report_names.index(selected)
        report_path = reports[idx]
        content = report_path.read_text(encoding="utf-8")

        # Afficher en markdown
        st.markdown("---")
        st.markdown(content)

        # Download button
        st.download_button(
            "📥 Download Report",
            data=content,
            file_name=report_path.name,
            mime="text/markdown",
        )


def page_history():
    """Page historique des scans"""
    st.markdown('<p class="main-header">📁 History</p>', unsafe_allow_html=True)

    reports = get_reports()
    if not reports:
        st.info("No history yet.")
        return

    # Tableau
    data = []
    for r in reports:
        meta = parse_report_metadata(r)
        if meta:
            data.append({
                "Target": meta["target"],
                "Found": f"{meta['found']}/{meta['total']}",
                "Enriched": "✅" if meta["enriched"] else "❌",
                "Date": meta["date"],
                "Size": f"{meta['size']//1024}KB",
            })

    st.dataframe(data, use_container_width=True, hide_index=True)

    # Export all
    if st.button("📥 Export All Reports (JSON)"):
        all_data = []
        for r in reports:
            meta = parse_report_metadata(r)
            if meta:
                content = r.read_text(encoding="utf-8")
                meta["content"] = content[:5000]
                all_data.append(meta)

        st.download_button(
            "Download",
            data=json.dumps(all_data, ensure_ascii=False, indent=2),
            file_name="ghost_all_reports.json",
            mime="application/json",
        )


def page_settings():
    """Page paramètres"""
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)

    st.subheader("Enrichment Server")
    col1, col2 = st.columns(2)
    with col1:
        enrich_url = st.text_input("Server URL", value="http://localhost:4567")
    with col2:
        enrich_key = st.text_input("API Key", type="password")

    st.subheader("Scan Defaults")
    col1, col2 = st.columns(2)
    with col1:
        default_deep = st.checkbox("Deep mode by default")
    with col2:
        default_enrich = st.checkbox("AI Enrichment by default", value=True)

    st.subheader("About")
    st.markdown("""
    **GHOST v0.2** — AI-Powered OSINT Engine
    
    - GitHub: [karim1811/ghost](https://github.com/karim1811/ghost)
    - Author: karim1811
    - License: MIT
    """)

    if st.button("💾 Save Settings"):
        st.success("Settings saved! (session only)")


# ── View Report Modal ───────────────────────────────────
if "view_report" in st.session_state:
    st.markdown("---")
    st.subheader("📄 Report Preview")
    try:
        content = Path(st.session_state["view_report"]).read_text(encoding="utf-8")
        st.markdown(content)
    except Exception as e:
        st.error(f"Cannot read report: {e}")
    if st.button("Close"):
        del st.session_state["view_report"]
        st.rerun()

# ── Router ──────────────────────────────────────────────
if page == "🏠 Home":
    page_home()
elif page == "🔍 New Scan":
    page_new_scan()
elif page == "📊 Reports":
    page_reports()
elif page == "📁 History":
    page_history()
elif page == "⚙️ Settings":
    page_settings()
