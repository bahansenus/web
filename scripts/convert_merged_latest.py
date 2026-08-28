#!/usr/bin/env python3
"""Convert the latest merged briefing HTML (from the n8n newsletter pipeline) into
a bahansen.us briefing page, reusing the existing verified content.

Source: /opt/data/docs/newsletters/merged-v37-verified-2026-08-28.html
Output: /opt/data/git/website/briefings/2026-08-28.html

The merged HTML body uses inline-styled Google Docs markup (h1 items, ul fields,
li bullets, span labels). We strip the outer wrapper and re-wrap the body content
inside the site chrome, then apply a small scoped stylesheet so the inline styles
(which reference fonts/colors) still render acceptably.
"""
import re
import sys
from pathlib import Path

SRC = Path("/opt/data/docs/newsletters/merged-v37-verified-2026-08-28.html")
OUT = Path("/opt/data/git/website/briefings/2026-08-28.html")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — bahansen.us</title>
  <meta name="description" content="{excerpt}">
  <link rel="stylesheet" href="/assets/style.css">
  <style>
    .briefing-body .merged {{ font-family: Inter, Arial, Helvetica, sans-serif; }}
    .briefing-body .merged h1 {{ font-size: 1.15rem; font-weight: 700; margin: 26px 0 6px; color: #2c3e50; line-height: 1.15; }}
    .briefing-body .merged p {{ margin: 0 0 10px; line-height: 1.4; color: #334155; }}
    .briefing-body .merged ul {{ padding-left: 20px; margin: 0 0 12px; list-style: none; }}
    .briefing-body .merged ul li {{ margin: 0 0 4px 18px; padding: 0; line-height: 1.4; color: #334155; font-size: 0.95rem; }}
    .briefing-body .merged a {{ color: #1155cc; text-decoration: underline; }}
    .briefing-body .merged .tier-marker {{ font-family: var(--mono); font-weight: 700; letter-spacing: 0.5px; margin-top: 30px; }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="/" class="brand">bahansen<span class="dot">.</span>us</a>
      <nav class="nav">
        <a href="/">Home</a>
        <a href="/briefings/">Briefings</a>
        <a href="/privacy">Privacy</a>
      </nav>
    </div>
  </header>

  <main class="container">
    <section class="briefing-header">
      <a href="/briefings/" class="back">← All briefings</a>
      <h1>{title}</h1>
      <div class="threat-line {threat_class}">Overall Daily Threat Level: {threat_level}.</div>
    </section>

    <div class="briefing-body">
      <div class="brief">{summary}</div>
      <div class="merged">
{body}
      </div>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <span>© 2026 bahansen.us</span>
      <span><a href="/privacy">Privacy Policy</a></span>
    </div>
  </footer>
</body>
</html>
"""


def strip_inline_styles(el_html: str) -> str:
    """Remove style attributes but keep structure and links."""
    el_html = re.sub(r'\s+style="[^"]*"', "", el_html)
    # Fix spans whose style attribute contained an inner quote (e.g.
    # style="...font-family:"Roboto Mono"") which breaks the regex above,
    # leaving a malformed <spanRoboto Mono"\"> opening tag. Repair it.
    el_html = re.sub(r'<spanRoboto Mono["\']*>', "<span>", el_html)
    return el_html


def convert() -> None:
    if not SRC.exists():
        print(f"ERROR: source not found: {SRC}", file=sys.stderr)
        sys.exit(1)

    raw = SRC.read_text()
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.S)
    if not m:
        print("ERROR: could not find <body> in source HTML", file=sys.stderr)
        sys.exit(1)
    body = m.group(1)

    title = "Daily Security Intelligence Briefing — August 28, 2026"
    threat_level = "CRITICAL"

    # Extract the executive summary: after "Overall Daily Threat Level: X." there
    # are spans — grab everything up to the tier-1 marker paragraph.
    summary = ""
    threat_pos = body.find("Overall Daily Threat Level:")
    if threat_pos >= 0:
        # find the end of the sentence "CRITICAL." and take up to TIER 1 marker
        tier_pos = body.find("TIER 1:", threat_pos)
        if tier_pos < 0:
            tier_pos = len(body)
        summary_slice = body[threat_pos:tier_pos]
        # remove the "Overall Daily Threat Level: CRITICAL." prefix up to the period
        m2 = re.search(r"Overall Daily Threat Level:\s*[A-Z]+\.", summary_slice)
        if m2:
            summary_slice = summary_slice[m2.end():]
        summary = re.sub(r"<[^>]+>", "", summary_slice)
        summary = summary.replace("&nbsp;", " ").strip()
        summary = re.sub(r"\s+", " ", summary)

    # Remove the threat-level summary paragraph from the body (it's now the brief)
    body = re.sub(
        r"<p[^>]*>Overall Daily Threat Level:.*?</p>", "", body, flags=re.S
    )

    # Remove the duplicated title + Executive Threat Brief headers from body
    body = re.sub(r"<h1[^>]*>Daily Security Intelligence Briefing.*?</h1>", "", body, flags=re.S)
    body = re.sub(r"<h1[^>]*>Executive Threat Brief.*?</h1>", "", body, flags=re.S)

    # Strip inline styles from the remaining body
    body = strip_inline_styles(body)

    # Fix malformed span tags from the Google export: <spanRoboto Mono"\">text</span>
    # (missing "<span " prefix — repair to a plain span). The literal bytes are
    # <spanRoboto Mono"> — match that exactly.
    body = re.sub(r"<spanRoboto Mono[\"']?\s*>", "<span>", body)

    # Remove empty paragraphs / whitespace-only lines for cleaner output
    body = re.sub(r"<p>\s*</p>", "", body)
    body = body.strip()

    # Build excerpt
    excerpt = summary[:150].replace('"', "")

    page = PAGE_TEMPLATE.format(
        title=title,
        threat_class="threat-critical",
        threat_level=threat_level,
        summary=summary,
        excerpt=excerpt,
        body=body,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    print(f"Wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    convert()
