#!/usr/bin/env python3
"""Validate the static site: every internal link/src resolves to a real file
relative to the page that references it. Runs from /opt/data/git/website."""
import re
from pathlib import Path

ROOT = Path("/opt/data/git/website")
# Ignore external http(s) links and anchors
EXTERNAL = re.compile(r"^(https?:)?//|^mailto:|^#")

def check_page(path: Path):
    html = path.read_text()
    refs = re.findall(r'(?:href|src)="([^"]+)"', html)
    errors = []
    seen = set()
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        if EXTERNAL.match(ref):
            continue
        # strip query/fragment
        ref_clean = ref.split("#")[0].split("?")[0]
        if not ref_clean:
            continue
        target = (path.parent / ref_clean).resolve()
        if not target.exists():
            errors.append(f"  BROKEN: '{ref}' (in {path.name} -> {target})")
    return errors

def main():
    all_errors = []
    pages = sorted(ROOT.glob("*.html")) + sorted((ROOT / "briefings").glob("*.html"))
    for p in pages:
        if p.name == "latest.html":
            continue
        errs = check_page(p)
        if errs:
            all_errors.extend(errs)
            print(f"{p.relative_to(ROOT)}:")
            for e in errs:
                print(e)
    if all_errors:
        print(f"\n{len(all_errors)} BROKEN LINKS")
        raise SystemExit(1)
    print(f"OK: checked {len(pages)} pages, all internal links resolve")

if __name__ == "__main__":
    main()
