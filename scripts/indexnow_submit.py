#!/usr/bin/env python3
"""Submit bahansen.us URLs to IndexNow (Bing, Yandex, Seznam, Naver, ...).

IndexNow is the only keyless, account-free submission path: proof of control is
the key file at https://bahansen.us/<KEY>.txt, which scripts/seo.py writes into
every deployment. Google does NOT participate in IndexNow — its sitemap +
Search Console route is separate.

Usage:
    python3 scripts/indexnow_submit.py                # URLs changed in the last N days
    python3 scripts/indexnow_submit.py --all          # every URL in the sitemap
    python3 scripts/indexnow_submit.py --url https://bahansen.us/briefings/2026-11-18

Exit codes: 0 submitted (200/202), 1 rejected, 2 could not reach the endpoint.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import seo  # noqa: E402

ENDPOINT = "https://api.indexnow.org/indexnow"
HOST = re.sub(r"^https?://", "", seo.SITE_BASE)


def sitemap_urls() -> list[tuple[str, str]]:
    """[(url, lastmod)] from the in-memory sitemap builder (no HTTP needed)."""
    xml = seo.build_sitemap(seo._entries_from_content())
    out = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
        if loc:
            out.append((loc.group(1), lm.group(1) if lm else ""))
    return out


def submit(urls: list[str]) -> int:
    body = {
        "host": HOST,
        "key": seo.INDEXNOW_KEY,
        "keyLocation": f"{seo.SITE_BASE}/{seo.INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"HTTP {r.status} — {len(urls)} URL(s) submitted")
            if r.status in (200, 202):
                print("  200 = accepted; 202 = accepted, key validation pending")
                return 0
            return 1
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        print(f"HTTP {e.code} — rejected: {detail}", file=sys.stderr)
        return 1
    except Exception as e:  # network/DNS/timeout
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="submit every sitemap URL")
    ap.add_argument("--days", type=int, default=3,
                    help="submit URLs with lastmod within N days (default 3)")
    ap.add_argument("--url", action="append", default=[],
                    help="submit an explicit URL (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.url:
        urls = a.url
    else:
        pages = sitemap_urls()
        if a.all:
            urls = [u for u, _ in pages]
        else:
            cutoff = (dt.date.today() - dt.timedelta(days=a.days)).isoformat()
            urls = [u for u, lm in pages if lm and lm >= cutoff]
            if not urls:  # nothing new — still refresh the front page
                urls = [seo.SITE_BASE + "/"]

    print(f"{len(urls)} URL(s):")
    for u in urls[:12]:
        print("  " + u)
    if len(urls) > 12:
        print(f"  ... and {len(urls) - 12} more")
    if a.dry_run:
        return 0
    return submit(urls)


if __name__ == "__main__":
    sys.exit(main())
