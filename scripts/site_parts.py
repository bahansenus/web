"""Shared HTML fragments for the bahansen.us static site.

All paths are depth-aware relative paths so the site works both at the GitHub
Pages project URL (/web/) and later at the custom domain root (bahansen.us).

Depth conventions:
  - root pages (index, about, history, privacy) are at the site root: depth=0
  - briefing pages live in briefings/: depth=1
"""
from pathlib import Path

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
      <span><a href="{root}articles.html">Articles</a> · <a href="{root}history.html">History</a> · <a href="{root}about.html">About</a> · <a href="{root}privacy.html">Privacy</a></span>
    </div>
  </footer>
'''

# ---------------------------------------------------------------- head --------
def head(title: str, description: str, depth: int = 0, extra_css: str = "", include_masthead: bool = True) -> str:
    root = "../" * depth
    css = f'  <link rel="stylesheet" href="{root}assets/style.css">\n'
    if extra_css:
        css += f"  <style>\n{extra_css}\n  </style>\n"
    mh = masthead(depth) if include_masthead else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
{css}</head>
<body>
{mh}
'''
