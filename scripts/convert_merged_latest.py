#!/usr/bin/env python3
"""Convert the latest merged briefing HTML (from the n8n newsletter pipeline) into
a bahansen.us briefing page AND the root landing page (index.html), reusing the
existing verified content.

Source: /opt/data/docs/newsletters/merged-v37-verified-2026-08-28.html
Output: /opt/data/git/website/briefings/2026-08-28.html
        /opt/data/git/website/index.html  (landing page when source is the latest)

The merged HTML body uses inline-styled Google Docs markup (h1 items, ul fields,
li bullets, span labels). We strip the outer wrapper and re-wrap the body content
inside the site chrome, then apply a small scoped stylesheet so the inline styles
(which reference fonts/colors) still render acceptably.

All paths are depth-aware relative (works at /web/ and at domain root).
"""
import re
import sys
from pathlib import Path

import site_parts

SRC = Path("/opt/data/docs/newsletters/merged-v37-verified-2026-08-28.html")
BRIEFING_OUT = Path("/opt/data/git/website/briefings/2026-08-28.html")
LANDING_OUT = Path("/opt/data/git/website/index.html")

BRIEFING_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <a href="../history.html" class="back">← All briefings</a>
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
{footer}
</body>
</html>
"""

LANDING_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>{title}</h1>
      <div class="threat-line {threat_class}">Overall Daily Threat Level: {threat_level}.</div>
    </section>

    <div class="briefing-body">
      <div class="brief">{summary}</div>
      <div class="merged">
{body}
      </div>
    </div>

    <p class="muted" style="margin-top:32px;"><a href="history.html">← View past briefings (History)</a></p>
  </main>
{footer}
</body>
</html>
"""

MERGE_CSS = """    .briefing-body .merged { font-family: Inter, Arial, Helvetica, sans-serif; }
    .briefing-body .merged h1 { font-size: 1.15rem; font-weight: 700; margin: 26px 0 6px; color: #2c3e50; line-height: 1.15; }
    .briefing-body .merged p { margin: 0 0 10px; line-height: 1.4; color: #334155; }
    .briefing-body .merged ul { padding-left: 20px; margin: 0 0 12px; list-style: none; }
    .briefing-body .merged ul li { margin: 0 0 4px 18px; padding: 0; line-height: 1.4; color: #334155; font-size: 0.95rem; }
    .briefing-body .merged a { color: #1155cc; text-decoration: underline; }
    .briefing-body .merged .tier-marker { font-family: var(--mono); font-weight: 700; letter-spacing: 0.5px; margin-top: 30px; }
"""


def strip_inline_styles(el_html: str) -> str:
    el_html = re.sub(r'\s+style="[^"]*"', "", el_html)
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

    # Extract the executive summary: after "Overall Daily Threat Level: X."
    summary = ""
    threat_pos = body.find("Overall Daily Threat Level:")
    if threat_pos >= 0:
        tier_pos = body.find("TIER 1:", threat_pos)
        if tier_pos < 0:
            tier_pos = len(body)
        summary_slice = body[threat_pos:tier_pos]
        m2 = re.search(r"Overall Daily Threat Level:\s*[A-Z]+\.", summary_slice)
        if m2:
            summary_slice = summary_slice[m2.end():]
        summary = re.sub(r"<[^>]+>", "", summary_slice)
        summary = summary.replace("&nbsp;", " ").strip()
        summary = re.sub(r"\s+", " ", summary)

    # Remove the threat-level summary paragraph, duplicated title, exec brief header
    body = re.sub(r"<p[^>]*>Overall Daily Threat Level:.*?</p>", "", body, flags=re.S)
    body = re.sub(r"<h1[^>]*>Daily Security Intelligence Briefing.*?</h1>", "", body, flags=re.S)
    body = re.sub(r"<h1[^>]*>Executive Threat Brief.*?</h1>", "", body, flags=re.S)

    body = strip_inline_styles(body)
    body = re.sub(r"<p>\s*</p>", "", body)
    body = body.strip()

    excerpt = summary[:150].replace('"', "")

    # Per-briefing page (depth 1)
    briefing = BRIEFING_TEMPLATE.format(
        head=site_parts.head(title, excerpt, depth=1, extra_css=MERGE_CSS),
        nav=site_parts.nav(depth=1, active="history"),
        title=title,
        threat_class="threat-critical",
        threat_level=threat_level,
        summary=summary,
        body=body,
        footer=site_parts.footer(depth=1),
    )
    BRIEFING_OUT.parent.mkdir(parents=True, exist_ok=True)
    BRIEFING_OUT.write_text(briefing)
    print(f"Wrote {BRIEFING_OUT} ({len(briefing)} bytes)")

    # Root landing page (depth 0)
    landing = LANDING_TEMPLATE.format(
        head=site_parts.head(title, excerpt, depth=0, extra_css=MERGE_CSS),
        nav=site_parts.nav(depth=0),
        title=title,
        threat_class="threat-critical",
        threat_level=threat_level,
        summary=summary,
        body=body,
        footer=site_parts.footer(depth=0),
    )
    LANDING_OUT.write_text(landing)
    print(f"Wrote {LANDING_OUT} (landing page, {len(landing)} bytes)")


if __name__ == "__main__":
    convert()
