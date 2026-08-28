#!/usr/bin/env python3
"""Inject the masthead logo banner into every briefing page that lacks it.

The briefing pages all share the same site-header block. This script inserts
the masthead <header> immediately before the existing <header class="site-header">.
Idempotent: skips pages that already contain the masthead.
"""
import sys
from pathlib import Path

OUT_DIR = Path("/opt/data/git/website/briefings")

MASTHEAD = """  <header class="masthead">
    <div class="container">
      <a href="/"><img src="/assets/logo.jpg" alt="BAHansen.us — Security Intelligence" class="logo"></a>
    </div>
  </header>
"""


def main():
    changed = 0
    skipped = 0
    for f in sorted(OUT_DIR.glob("*.html")):
        if f.name == "index.html":
            continue  # already updated manually
        html = f.read_text()
        if "masthead" in html:
            skipped += 1
            continue
        marker = '<header class="site-header">'
        if marker not in html:
            print(f"  SKIP (no site-header): {f.name}")
            continue
        html = html.replace(marker, MASTHEAD + marker, 1)
        f.write_text(html)
        print(f"  updated: {f.name}")
        changed += 1
    print(f"Done: {changed} updated, {skipped} already had masthead")


if __name__ == "__main__":
    main()
