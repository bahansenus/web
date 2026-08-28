#!/usr/bin/env python3
"""Rebuild the entire bahansen.us static site from source content.

Run from /opt/data/git/website (site_parts.py must be importable):
    python3 scripts/build_site.py

Steps:
  1. Convert all .txt briefings -> briefings/YYYY-MM-DD.html + latest -> index.html
  2. Convert the latest merged HTML (if present) -> briefings/2026-08-28.html + index.html
  3. Build history.html, about.html, privacy.html
"""
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/data/git/website")
SCRIPTS = REPO / "scripts"


def run(name: str):
    print(f"\n=== {name} ===")
    r = subprocess.run([sys.executable, str(SCRIPTS / name)], cwd=SCRIPTS, capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)


def main():
    run("convert_briefings.py")
    # The merged latest is only for 2026-08-28 (no txt source for that day).
    run("convert_merged_latest.py")
    run("build_history.py")
    run("build_about.py")
    run("build_privacy.py")
    print("\n=== BUILD COMPLETE ===")


if __name__ == "__main__":
    main()
