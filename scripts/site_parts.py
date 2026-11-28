"""Shared HTML fragments for the bahansen.us static site.

All paths are depth-aware relative paths so the site works both at the GitHub
Pages project URL (/web/) and later at the custom domain root (bahansen.us).

Depth conventions:
  - root pages (index, about, history, privacy) are at the site root: depth=0
  - briefing pages live in briefings/: depth=1
"""
import html as html_mod
from pathlib import Path

import seo

# ---------------------------------------------------------------- masthead ---
def masthead(depth: int = 0) -> str:
    root = "../" * depth
    return f'''  <header class="masthead">
    <div class="container">
      <a href="{root}index.html"><img src="{root}assets/logo.jpg" alt="BAHansen.us — Security Intelligence" class="logo"></a>
    </div>
  </header>
'''

# ---------------------------------------------------------------- navigation --
def nav(depth: int = 0, active: str = "") -> str:
    """active: one of '' (none), 'articles', 'history', 'about', 'privacy'"""
    root = "../" * depth
    links = []
    for href, label, key in (
        ("articles.html", "Articles", "articles"),
        ("history.html", "History", "history"),
        ("about.html", "About", "about"),
        ("privacy.html", "Privacy", "privacy"),
    ):
        cls = ' class="active"' if key == active else ""
        links.append(f'        <a href="{root}{href}"{cls}>{label}</a>')
    return f'''  <header class="site-header">
    <div class="container">
      <a href="{root}index.html" class="brand">bahansen<span class="dot">.</span>us</a>
      <nav class="nav">
{chr(10).join(links)}
      </nav>
    </div>
  </header>
'''

# ---------------------------------------------------------------- footer ------
def footer(depth: int = 0) -> str:
    root = "../" * depth
    return f'''  <footer class="site-footer">
    <div class="container">
      <span>© 2026 bahansen.us</span>
      <span><a href="{root}articles.html">Articles</a> · <a href="{root}history.html">History</a> · <a href="{root}about.html">About</a> · <a href="{root}privacy.html">Privacy</a> · <a href="{root}tools/dmarc/">Tools</a></span>
    </div>
  </footer>
'''

# ---------------------------------------------------------------- head --------
def head(title: str, description: str, depth: int = 0, extra_css: str = "",
         include_masthead: bool = True, canonical: str = "",
         og_type: str = "website", jsonld: str = "",
         noindex: bool = False) -> str:
    """Page <head>. `canonical` is a site path ('/', '/about',
    '/briefings/2026-11-18') — the extensionless form Cloudflare Pages serves
    with a 200; the .html form is a 308 and must never be canonical."""
    root = "../" * depth
    # Descriptions are plain text from the renderer; escape them for use in
    # attributes so a '&' or '<' in a summary cannot corrupt the tag.
    description = html_mod.escape(description, quote=True)
    css = f'  <link rel="stylesheet" href="{root}assets/style.css">\n'
    if extra_css:
        css += f"  <style>\n{extra_css}\n  </style>\n"

    seo_tags = []
    if noindex:
        seo_tags.append('  <meta name="robots" content="noindex, follow">')
    else:
        seo_tags.append('  <meta name="robots" content="index, follow, '
                        'max-image-preview:large, max-snippet:-1">')
    if canonical:
        url = seo.canonical(canonical)
        seo_tags += [
            f'  <link rel="canonical" href="{url}">',
            f'  <meta property="og:url" content="{url}">',
        ]
    seo_tags += [
        '  <link rel="alternate" type="application/rss+xml" '
        f'title="Daily Security Intelligence Briefing — bahansen.us" '
        f'href="{seo.SITE_BASE}/feed.xml">',
        f'  <link rel="icon" type="image/png" sizes="192x192" '
        f'href="{root}assets/favicon-192.png">',
        f'  <link rel="apple-touch-icon" href="{root}assets/apple-touch-icon.png">',
        '  <meta property="og:site_name" content="bahansen.us">',
        f'  <meta property="og:type" content="{og_type}">',
        f'  <meta property="og:title" content="{html_mod.escape(title, quote=True)}">',
        f'  <meta property="og:description" content="{description}">',
        f'  <meta property="og:image" content="{seo.SITE_BASE}/assets/og-card.png">',
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        '  <meta property="og:image:alt" content="bahansen.us — Daily Security '
        'Intelligence Briefing">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{html_mod.escape(title, quote=True)}">',
        f'  <meta name="twitter:description" content="{description}">',
        f'  <meta name="twitter:image" content="{seo.SITE_BASE}/assets/og-card.png">',
    ]
    if jsonld:
        seo_tags.append(jsonld)
    seo_block = "\n".join(seo_tags) + "\n"

    mh = masthead(depth) if include_masthead else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_mod.escape(title, quote=False)}</title>
  <meta name="description" content="{description}">
{seo_block}{css}  <script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "8d5e9a88082a4e16ad85726f40747986"}}'></script>
</head>
<body>
{mh}
'''
