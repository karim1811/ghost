# GHOST — Render Deployment Script
# Run this after pushing to GitHub

import subprocess
import sys
import os

def run(cmd):
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(1)

def main():
    print("""
  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝
  ██║  ███╗███████║██║   ██║███████╗   ██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═════╝   ╚═╝
   Render Deployment Script
""")

    # Check render CLI
    result = subprocess.run("render --version", shell=True, capture_output=True)
    if result.returncode != 0:
        print("Installing Render CLI...")
        run("npm install -g @render-cli/render-cli")

    # Login
    print("\n[1/4] Login to Render...")
    run("render login")

    # Push to GitHub
    print("\n[2/4] Push to GitHub...")
    run("git add -A")
    run('git commit -m "deploy: ready for render"')
    run("git push origin main")

    # Deploy
    print("\n[3/4] Deploying to Render...")
    run("render blueprint apply render.yaml")

    # Done
    print("\n[4/4] Done!")
    print("""
Your GHOST services are deploying:

  API:          https://ghost-api.onrender.com
  Enrichment:  https://ghost-enrich.onrender.com
  Bot:         (worker, no URL)

Check status: render services
View logs:     render logs ghost-api

Set your API keys in the Render dashboard:
  → https://dashboard.render.com
    """)

if __name__ == "__main__":
    main()
