#!/usr/bin/env python3
"""Convert Daily Security Intelligence Briefing .txt files into styled HTML
briefing pages for the bahansen.us static site.

Source files: /opt/data/docs/newsletters/Daily Security Intelligence Briefing - YYYY-MM-DD.txt
Output:       /opt/data/git/website/briefings/YYYY-MM-DD.html

Also writes the two "latest" landing pages:
  - /opt/data/git/website/index.html        (root landing = latest briefing)
  - /opt/data/git/website/briefings/latest.html (briefings dir copy, not linked)

The txt format (verified on real briefings):
  Line 1:  "Daily Security Intelligence Briefing — Month DD, YYYY"
  Line 2:  "Executive Threat Brief"
  Line 3:  "Overall Daily Threat Level: LEVEL."
  Then:    executive summary paragraph(s)
  "TIER 1: PRIORITY TARGETS (MUST-READ)"  -> numbered items with * field labels
  "TIER 2: ESSENTIAL INTELLIGENCE (SUMMARIES & ANALYSIS)"
  "TIER 3: INDUSTRY NOISE & AWARENESS ONLY" -> * bullets

All paths are depth-aware relative (works at /web/ and at domain root).
"""
import html
import re
import sys
from pathlib import Path

import site_parts

SRC_DIR = Path("/opt/data/docs/newsletters")
OUT_DIR = Path("/opt/data/git/website/briefings")
ROOT_OUT = Path("/opt/data/git/website")

# Landing-page template: the full briefing body served at the site root.
LANDING_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>{title}</h1>
      <div class="threat-line {threat_class}">Overall Daily Threat Level: {threat_level}.</div>
      <p class="muted">{date_label}</p>
    </section>

    <div class="briefing-body">
      <div class="brief">{summary}</div>
      {body}
    </div>

    <p class="muted" style="margin-top:32px;"><a href="history.html">← View past briefings (History)</a></p>
  </main>
{footer}
</body>
</html>
"""

# Per-briefing page template (in briefings/ subdir, depth=1).
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
      {body}
    </div>
  </main>
{footer}
</body>
</html>
"""


def threat_class(level: str) -> str:
    level = level.upper()
    if "CRITICAL" in level:
        return "threat-critical"
    if "HIGH" in level:
        return "threat-high"
    if "MODERATE" in level:
        return "threat-moderate"
    return "threat-low"


def parse_briefing(text: str) -> dict:
    """Parse a briefing txt into structured sections."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = [l.rstrip() for l in text.split("\n")]

    title = lines[0].strip() if lines else ""
    date_match = re.search(r"(\w+ \d{1,2}, \d{4})$", title)

    threat_line = ""
    for l in lines[1:6]:
        if "Overall Daily Threat Level" in l:
            threat_line = l.strip()
            break
    threat_level = re.sub(r"Overall Daily Threat Level:\s*", "", threat_line).rstrip(".").strip()

    tier_idx = {"t1": -1, "t2": -1, "t3": -1}
    for i, l in enumerate(lines):
        if "TIER 1:" in l and tier_idx["t1"] < 0:
            tier_idx["t1"] = i
        elif "TIER 2:" in l and tier_idx["t2"] < 0:
            tier_idx["t2"] = i
        elif "TIER 3:" in l and tier_idx["t3"] < 0:
            tier_idx["t3"] = i

    t1_start = tier_idx["t1"] if tier_idx["t1"] >= 0 else len(lines)
    summary_lines = []
    for l in lines[3: t1_start]:
        if not l.strip():
            continue
        if "TIER" in l and ":" in l:
            break
        summary_lines.append(l.strip())
    summary = " ".join(summary_lines)

    t2_start = tier_idx["t2"] if tier_idx["t2"] >= 0 else len(lines)
    t3_start = tier_idx["t3"] if tier_idx["t3"] >= 0 else len(lines)

    def tier_block(start, end):
        if start < 0:
            return []
        return [l.strip() for l in lines[start + 1: end] if l.strip()]

    t1 = tier_block(tier_idx["t1"], t2_start if tier_idx["t2"] >= 0 else t3_start if tier_idx["t3"] >= 0 else len(lines))
    t2 = tier_block(tier_idx["t2"], t3_start if tier_idx["t3"] >= 0 else len(lines))
    t3 = tier_block(tier_idx["t3"], len(lines))

    return {
        "title": title,
        "date": date_match.group(1) if date_match else "",
        "threat_level": threat_level,
        "threat_class": threat_class(threat_level),
        "summary": html.escape(summary),
        "t1": t1,
        "t2": t2,
        "t3": t3,
    }


def render_tier_items(block_lines: list) -> str:
    items = []
    current = None
    for line in block_lines:
        if re.match(r"^\d+\.\s", line):
            if current:
                items.append(current)
            current = {"title": line, "fields": []}
        elif line.startswith("*") and current is not None:
            current["fields"].append(line.lstrip("* ").strip())
        else:
            if current is not None:
                if current["fields"]:
                    current["fields"][-1] += " " + line
                else:
                    current["title"] += " " + line
    if current:
        items.append(current)

    out = []
    for item in items:
        out.append('<div class="item">')
        out.append(f'<h3>{html.escape(item["title"])}</h3>')
        for field in item["fields"]:
            m = re.match(r"^([^:]+):\s*(.*)$", field, re.S)
            if m:
                label, value = m.group(1), m.group(2)
                out.append(f'<p><span class="label">{html.escape(label)}:</span> {html.escape(value)}</p>')
            else:
                out.append(f"<p>{html.escape(field)}</p>")
        out.append("</div>")
    return "\n".join(out)


def render_tier3(block_lines: list) -> str:
    out = ['<div class="item">']
    out.append("<h3>Tier 3 — Industry Noise &amp; Awareness Only</h3>")
    for line in block_lines:
        line = line.lstrip("* ").strip()
        if line:
            out.append(f"<p>• {html.escape(line)}</p>")
    out.append("</div>")
    return "\n".join(out)


def render_body(data: dict) -> str:
    t1_html = render_tier_items(data["t1"])
    t2_html = render_tier_items(data["t2"])
    t3_html = render_tier3(data["t3"])

    body = []
    if t1_html:
        body.append("<h2>Tier 1 — Priority Targets (Must-Read)</h2>")
        body.append(t1_html)
    if t2_html:
        body.append("<h2>Tier 2 — Essential Intelligence (Summaries &amp; Analysis)</h2>")
        body.append(t2_html)
    if t3_html:
        body.append(t3_html)
    return "\n".join(body)


def convert_file(path: Path, date_str: str) -> None:
    data = parse_briefing(path.read_text())
    body = render_body(data)
    excerpt = html.escape(data["summary"][:150])

    # Per-briefing page (depth 1)
    page = BRIEFING_TEMPLATE.format(
        head=site_parts.head(data["title"], excerpt, depth=1),
        nav=site_parts.nav(depth=1, active="history"),
        title=data["title"],
        threat_class=data["threat_class"],
        threat_level=data["threat_level"],
        summary=data["summary"],
        body=body,
        footer=site_parts.footer(depth=1),
    )
    out = OUT_DIR / f"{date_str}.html"
    out.write_text(page)
    print(f"  briefing: {date_str} -> {out.name} ({len(page)} bytes)")

    # Latest landing page at root (depth 0) — only for the newest date
    if date_str == max_date_str:
        landing = LANDING_TEMPLATE.format(
            head=site_parts.head(data["title"], excerpt, depth=0),
            nav=site_parts.nav(depth=0),
            title=data["title"],
            threat_class=data["threat_class"],
            threat_level=data["threat_level"],
            date_label=data["date"],
            summary=data["summary"],
            body=body,
            footer=site_parts.footer(depth=0),
        )
        (ROOT_OUT / "index.html").write_text(landing)
        print(f"  LANDING: {date_str} -> index.html ({len(landing)} bytes)")


max_date_str = ""


def main():
    global max_date_str
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pattern = sys.argv[1] if len(sys.argv) > 1 else "*"
    files = sorted(SRC_DIR.glob(f"Daily Security Intelligence Briefing - {pattern}.txt"))
    dated = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if m:
            dated.append((m.group(1), f))
    if not dated:
        print("No briefing txt files found")
        sys.exit(1)
    max_date_str = max(d[0] for d in dated)

    for date_str, f in dated:
        convert_file(f, date_str)

    print(f"Done: {len(dated)} briefings -> {OUT_DIR}, landing -> index.html")


if __name__ == "__main__":
    main()
