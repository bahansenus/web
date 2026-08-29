#!/usr/bin/env python3
"""Rebuild the entire bahansen.us static site from raw content in content/.

Run from /opt/data/git/website:
    python3 scripts/build_site.py

Steps:
  1. render.py  — read content/briefings + content/articles, render _site/
  2. validate_links.py — check every internal link in _site/ resolves

Output lands in _site/ (gitignored). GitHub Actions builds, validates, then
deploys _site/ to GitHub Pages.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def run(name: str, extra_args: list[str] | None = None):
    print(f"\n=== {name} ===")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(extra_args or [])],
        capture_output=True, text=True,
    )
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)


def main():
    run("render.py")
    run("validate_links.py", ["_site"])
    print("\n=== BUILD COMPLETE: _site/ is ready to deploy ===")


if __name__ == "__main__":
    main()
