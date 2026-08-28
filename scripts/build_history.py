#!/usr/bin/env python3
"""Build the History page (archive index) for bahansen.us.

Scans the generated briefing pages in briefings/ and builds history.html
listing every edition newest-first with date, title, and threat level.

All paths are depth-aware relative (works at /web/ and at domain root).
"""
import re
from pathlib import Path

import site_parts

BRIEFINGS_DIR = Path("/opt/data/git/website/briefings")
OUT = Path("/opt/data/git/website/history.html")

TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>History — Past Briefings</h1>
      <p style="color:var(--text-dim);">Every edition of the Daily Security Intelligence Briefing, newest first. The latest edition is always the landing page.</p>
    </section>

    <div class="briefings-list">
{cards}
    </div>
  </main>
{footer}
</body>
</html>
"""

CARD_TEMPLATE = """      <div class="card">
        <div class="date">{date_label}{latest_tag}</div>
        <h3><a href="briefings/{filename}">{title}</a></h3>
        <p class="mono muted">{threat_line}</p>
      </div>
"""


def parse_briefing_page(path: Path) -> dict | None:
    html = path.read_text()
    title_m = re.search(r"<h1>(.*?)</h1>", html, re.S)
    threat_m = re.search(r"Overall Daily Threat Level:\s*([A-Z]+)", html)
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not title_m or not date_m:
        return None
    title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
    return {
        "filename": path.name,
        "date": date_m.group(1),
        "title": title,
        "threat": threat_m.group(1) if threat_m else "",
    }


def main():
    entries = []
    for f in sorted(BRIEFINGS_DIR.glob("*.html")):
        if f.name == "latest.html":
            continue
        e = parse_briefing_page(f)
        if e:
            entries.append(e)
    entries.sort(key=lambda e: e["date"], reverse=True)

    cards = []
    for i, e in enumerate(entries):
        latest = " · LATEST" if i == 0 else ""
        # format date label like "August 28, 2026"
        try:
            from datetime import datetime
            date_label = datetime.strptime(e["date"], "%Y-%m-%d").strftime("%B %-d, %Y")
        except Exception:
            date_label = e["date"]
        cards.append(CARD_TEMPLATE.format(
            date_label=date_label,
            latest_tag=latest,
            filename=e["filename"],
            title=e["title"],
            threat_line=f"Overall Daily Threat Level: {e['threat']}" if e["threat"] else "",
        ))

    page = TEMPLATE.format(
        head=site_parts.head("History — Past Briefings — bahansen.us",
                             "Archive of Daily Security Intelligence Briefings from bahansen.us.", depth=0),
        nav=site_parts.nav(depth=0, active="history"),
        cards="\n".join(cards),
        footer=site_parts.footer(depth=0),
    )
    OUT.write_text(page)
    print(f"Wrote {OUT} ({len(entries)} entries, {len(page)} bytes)")


if __name__ == "__main__":
    main()
