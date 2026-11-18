#!/usr/bin/env python3
"""Search-engine discoverability artifacts for bahansen.us.

Writes four things into _site/ so they are deployed with every build:

  robots.txt              crawl policy + sitemap discovery
  sitemap.xml             every canonical URL, with a real <lastmod>
  <INDEXNOW_KEY>.txt      IndexNow key file (ownership proof for the API)
  404.html                a real not-found page, so unknown paths answer 404
                          instead of silently serving the homepage with 200

Design notes
------------
* Canonical URLs are the EXTENSIONLESS ones ("/history", "/briefings/2026-11-18").
  Cloudflare Pages answers those with 200 and 308-redirects the ".html" form to
  them, so the .html URL must never appear in a sitemap or a canonical tag.
* Content pages keep their .html hyperlinks on purpose: the GitHub Pages
  fallback deploy target has no clean-URL rewriting, and a 308 hop is
  crawlable. Canonicalisation, not link rewriting, is what fixes duplication.
* Nothing here performs network I/O. Submitting URLs to IndexNow lives in
  scripts/indexnow_submit.py so a build stays offline and deterministic.
"""
from __future__ import annotations

import html as html_mod
import json

SITE_BASE = "https://bahansen.us"  # public origin; never the github.io project URL

# IndexNow ownership proof: served at https://bahansen.us/<KEY>.txt and sent
# with every submission. Changing it invalidates the deployed key file, so the
# build writes the file from this constant — never hand-edit one without the
# other.
INDEXNOW_KEY = "e1ab65988c3eb71db436428b949bb4b6"

# Pages that are not briefings: (path, changefreq, priority)
STATIC_PAGES = [
    ("/", "daily", "1.0"),
    ("/history", "daily", "0.7"),
    ("/articles", "weekly", "0.5"),
    ("/about", "monthly", "0.3"),
    ("/privacy", "yearly", "0.1"),
]


def canonical(path: str) -> str:
    """Absolute canonical URL for a site path ('/', '/about', '/briefings/...')."""
    if not path.startswith("/"):
        path = "/" + path
    return SITE_BASE + "/" if path == "/" else SITE_BASE + path


# ------------------------------------------------------------------ JSON-LD ---

def _organization() -> dict:
    return {
        "@type": "Organization",
        "@id": f"{SITE_BASE}/#organization",
        "name": "bahansen.us",
        "url": SITE_BASE + "/",
        "logo": {
            "@type": "ImageObject",
            "url": f"{SITE_BASE}/assets/logo.jpg",
        },
        "founder": {
            "@type": "Person",
            "name": "Brett Hansen",
            "url": f"{SITE_BASE}/about",
        },
    }


def jsonld(page_path: str, title: str, description: str,
           published_iso: str | None = None) -> str:
    """Return a <script> block of JSON-LD for one page.

    Every page gets Organization + WebSite + WebPage. A briefing page (one with
    a published timestamp) additionally gets NewsArticle + BreadcrumbList,
    which is what makes the page eligible for article rich results.
    """
    graph: list[dict] = [
        _organization(),
        {
            "@type": "WebSite",
            "@id": f"{SITE_BASE}/#website",
            "url": SITE_BASE + "/",
            "name": "bahansen.us",
            "description": "Daily Security Intelligence Briefing — threat "
                           "intelligence, vulnerability and supply-chain "
                           "analysis for operators.",
            "publisher": {"@id": f"{SITE_BASE}/#organization"},
            "inLanguage": "en",
        },
    ]

    page: dict = {
        "@type": "WebPage",
        "@id": canonical(page_path) + "#webpage",
        "url": canonical(page_path),
        "name": title,
        "description": description,
        "isPartOf": {"@id": f"{SITE_BASE}/#website"},
        "inLanguage": "en",
    }

    if published_iso:
        article = {
            "@type": "NewsArticle",
            "@id": canonical(page_path) + "#article",
            "headline": title,
            "description": description,
            "datePublished": published_iso,
            "dateModified": published_iso,
            "mainEntityOfPage": {"@id": canonical(page_path) + "#webpage"},
            "isPartOf": {"@id": f"{SITE_BASE}/#website"},
            "publisher": {"@id": f"{SITE_BASE}/#organization"},
            "author": {
                "@type": "Person",
                "name": "Brett Hansen",
                "url": f"{SITE_BASE}/about",
            },
            "inLanguage": "en",
            "isAccessibleForFree": True,
            "image": [f"{SITE_BASE}/assets/logo.jpg"],
        }
        page["mainEntity"] = {"@id": canonical(page_path) + "#article"}
        graph.append(article)
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1,
                 "name": "Briefings", "item": f"{SITE_BASE}/history"},
                {"@type": "ListItem", "position": 2, "name": title},
            ],
        })

    graph.append(page)
    payload = {"@context": "https://schema.org", "@graph": graph}
    return (
        '  <script type="application/ld+json">'
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


# ----------------------------------------------------------------- artifacts --

def build_robots() -> str:
    return (
        "# bahansen.us — generated by scripts/seo.py; do not hand-edit in _site/\n"
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "# Cloudflare-injected endpoints are not content.\n"
        "Disallow: /cdn-cgi/\n"
        "\n"
        f"Sitemap: {SITE_BASE}/sitemap.xml\n"
    )


def build_sitemap(entries: list[dict]) -> str:
    """entries: [{date: 'YYYY-MM-DD', ...}] newest first, as render.py builds them."""
    urls: list[tuple[str, str, str, str]] = []  # (loc, lastmod, changefreq, priority)
    latest = entries[0]["date"] if entries else ""

    for path, freq, prio in STATIC_PAGES:
        loc = canonical(path)
        lastmod = latest if path in ("/", "/history") else ""
        urls.append((loc, lastmod, freq, prio))

    for e in sorted(entries, key=lambda x: x["date"], reverse=True):
        urls.append((
            canonical(f"/briefings/{e['date']}"),
            e["date"],
            "monthly",   # an edition never changes once published
            "0.8",
        ))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, freq, prio in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{html_mod.escape(loc)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{prio}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_404() -> str:
    """A real 404 page. Cloudflare Pages serves 404.html with a 404 status.

    Every href here is ABSOLUTE: the page is served for arbitrary depths
    (/foo/bar), where a relative "assets/style.css" would resolve to
    /foo/assets/style.css and 404 again.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page not found — bahansen.us</title>
  <meta name="robots" content="noindex, follow">
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="/index.html" class="brand">bahansen<span class="dot">.</span>us</a>
      <nav class="nav">
        <a href="/articles.html">Articles</a>
        <a href="/history.html">History</a>
        <a href="/about.html">About</a>
        <a href="/privacy.html">Privacy</a>
      </nav>
    </div>
  </header>

  <main class="container">
    <section class="briefing-header">
      <h1>Page not found</h1>
      <p class="muted">That URL doesn't exist on this site.</p>
    </section>
    <div class="briefing-body">
      <p>The daily briefing is published on the <a href="/index.html">front page</a>, and every
         past edition is listed in the <a href="/history.html">archive</a>.</p>
      <p class="muted">Editions keep permanent URLs of the form
         <code>bahansen.us/briefings/YYYY-MM-DD</code>.</p>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <span>© 2026 bahansen.us</span>
      <span><a href="/articles.html">Articles</a> · <a href="/history.html">History</a> · <a href="/about.html">About</a> · <a href="/privacy.html">Privacy</a></span>
    </div>
  </footer>
</body>
</html>
"""


def write_all(out_dir) -> None:
    """Write every artifact into the build output directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sitemap_entries = _entries_from_content()
    (out_dir / "robots.txt").write_text(build_robots())
    (out_dir / "sitemap.xml").write_text(build_sitemap(sitemap_entries))
    (out_dir / "404.html").write_text(build_404())
    (out_dir / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY + "\n")
    print(f"  robots.txt, sitemap.xml ({len(sitemap_entries)} briefings), "
          f"404.html, {INDEXNOW_KEY}.txt")


def _entries_from_content() -> list[dict]:
    """Read briefing dates straight from content/ so the sitemap is complete
    even if called outside render.py's own entry list."""
    from pathlib import Path
    import re

    content = Path(__file__).resolve().parent.parent / "content" / "briefings"
    seen: dict[str, dict] = {}
    for f in sorted(content.glob("*")):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not m:
            continue
        # .json supersedes the legacy .html twin for the same date
        if m.group(1) in seen and f.suffix != ".json":
            continue
        seen[m.group(1)] = {"date": m.group(1)}
    return [seen[d] for d in sorted(seen, reverse=True)]
