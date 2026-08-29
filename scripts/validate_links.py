#!/usr/bin/env python3
"""Validate a static site: every internal link/src resolves to a real file
relative to the page that references it.

Usage: python3 validate_links.py [site_dir]   (default: _site)
"""
import re
import sys
from pathlib import Path

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
        ref_clean = ref.split("#")[0].split("?")[0]
        if not ref_clean:
            continue
        target = (path.parent / ref_clean).resolve()
        if not target.exists():
            errors.append(f"  BROKEN: '{ref}' (in {path.name} -> {target})")
    return errors


def main():
    root_arg = sys.argv[1] if len(sys.argv) > 1 else "_site"
    root = Path(root_arg).resolve()
    if not root.exists():
        print(f"ERROR: {root} does not exist")
        sys.exit(1)

    all_errors = []
    pages = sorted(root.glob("*.html")) + sorted((root / "briefings").glob("*.html"))
    if (root / "articles").exists():
        pages += sorted((root / "articles").glob("*.html"))
    for p in pages:
        errs = check_page(p)
        if errs:
            all_errors.extend(errs)
            print(f"{p.relative_to(root)}:")
            for e in errs:
                print(e)
    if all_errors:
        print(f"\n{len(all_errors)} BROKEN LINKS")
        raise SystemExit(1)
    print(f"OK: checked {len(pages)} pages in {root}, all internal links resolve")


if __name__ == "__main__":
    main()
