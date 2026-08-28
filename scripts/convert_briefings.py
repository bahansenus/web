#!/usr/bin/env python3
"""Convert Daily Security Intelligence Briefing .txt files into styled HTML
briefing pages for the bahansen.us static site.

Source files: /opt/data/docs/newsletters/Daily Security Intelligence Briefing - YYYY-MM-DD.txt
Output:       /opt/data/git/website/briefings/YYYY-MM-DD.html

The txt format (verified on real briefings):
  Line 1:  "Daily Security Intelligence Briefing — Month DD, YYYY"
  Line 2:  "Executive Threat Brief"
  Line 3:  "Overall Daily Threat Level: LEVEL."
  Then:    executive summary paragraph(s)
  "TIER 1: PRIORITY TARGETS (MUST-READ)"  -> numbered items with * field labels
  "TIER 2: ESSENTIAL INTELLIGENCE (SUMMARIES & ANALYSIS)"
  "TIER 3: INDUSTRY NOISE & AWARENESS ONLY" -> * bullets
"""
import html
import re
import sys
from datetime import datetime
from pathlib import Path

SRC_DIR = Path("/opt/data/docs/newsletters")
OUT_DIR = Path("/opt/data/git/website/briefings")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — bahansen.us</title>
  <meta name="description" content="{excerpt}">
  <link rel="stylesheet" href="/assets/style.css">
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
      {body}
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
    # normalize line endings, strip BOM
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = [l.rstrip() for l in text.split("\n")]

    title = lines[0].strip() if lines else ""
    # Extract date from title: "Daily Security Intelligence Briefing — August 10, 2026"
    date_match = re.search(r"(\w+ \d{1,2}, \d{4})$", title)

    # Threat level
    threat_line = ""
    for l in lines[1:6]:
        if "Overall Daily Threat Level" in l:
            threat_line = l.strip()
            break
    threat_level = re.sub(r"Overall Daily Threat Level:\s*", "", threat_line).rstrip(".").strip()

    # Locate tier headers
    tier_idx = {"t1": -1, "t2": -1, "t3": -1}
    for i, l in enumerate(lines):
        if "TIER 1:" in l and tier_idx["t1"] < 0:
            tier_idx["t1"] = i
        elif "TIER 2:" in l and tier_idx["t2"] < 0:
            tier_idx["t2"] = i
        elif "TIER 3:" in l and tier_idx["t3"] < 0:
            tier_idx["t3"] = i

    # Executive summary = lines between threat level and TIER 1
    t1_start = tier_idx["t1"] if tier_idx["t1"] >= 0 else len(lines)
    summary_lines = []
    for l in lines[3: t1_start]:
        if not l.strip():
            continue
        if "TIER" in l and ":" in l:
            break
        summary_lines.append(l.strip())
    summary = " ".join(summary_lines)

    # Extract tier blocks
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
    """Render tier 1/2 items: numbered headings + * field lines."""
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
            # continuation / orphan line -> append to last field or title
            if current is not None:
                if current["fields"]:
                    current["fields"][-1] += " " + line
                else:
                    current["title"] += " " + line
    if current:
        items.append(current)

    out = []
    for item in items:
        # extract field label prefix ("Source & Article Link: ...")
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
    """Render tier 3 as bullet list items."""
    out = ['<div class="item">']
    out.append("<h3>Tier 3 — Industry Noise &amp; Awareness Only</h3>")
    for line in block_lines:
        line = line.lstrip("* ").strip()
        if line:
            out.append(f"<p>• {html.escape(line)}</p>")
    out.append("</div>")
    return "\n".join(out)


def convert_file(path: Path) -> str:
    data = parse_briefing(path.read_text())
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

    # excerpt for meta description
    excerpt = html.escape(data["summary"][:150])

    return PAGE_TEMPLATE.format(
        title=data["title"],
        excerpt=excerpt,
        threat_class=data["threat_class"],
        threat_level=data["threat_level"],
        summary=data["summary"],
        body="\n".join(body),
    )


def main():
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = sys.argv[1] if len(sys.argv) > 1 else "*"
    files = sorted(SRC_DIR.glob(f"Daily Security Intelligence Briefing - {pattern}.txt"))

    # Also handle the latest merged HTML briefing if present
    extra = []
    if len(sys.argv) > 1 and sys.argv[1] == "2026-08-28":
        merged = SRC_DIR / "merged-v37-verified-2026-08-28.html"
        if merged.exists():
            extra.append(merged)

    count = 0
    for f in files:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not date_match:
            print(f"  SKIP (no date in name): {f.name}")
            continue
        date_str = date_match.group(1)
        page = convert_file(f)
        out = out_dir / f"{date_str}.html"
        out.write_text(page)
        print(f"  {date_str}: {len(f.read_text())} bytes src -> {out.name}")
        count += 1

    print(f"Converted {count} briefings to {out_dir}")


if __name__ == "__main__":
    main()
