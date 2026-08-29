#!/usr/bin/env python3
"""Unified renderer for the bahansen.us static site — the "theme engine".

Reads raw content files from content/ and renders complete pages into _site/:

  content/briefings/YYYY-MM-DD.html   -> _site/briefings/YYYY-MM-DD.html
                                        + _site/index.html (latest edition)
  content/articles/*.html             -> _site/articles/*.html  (scaffold)
  (generated)                         -> _site/history.html, _site/feed.xml

Two content formats are supported per briefing:
  - Google-Docs merged export (what n8n produces): full inline-styled HTML
    body; the renderer strips inline styles and relies on the theme CSS.
  - Normalized tier body (.brief-summary + .tier h2 + .tier-item): direct.

All rendered pages use depth-aware relative paths so the site works both at
the GitHub Pages project URL (/web/) and at a future custom-domain root.

Theme = assets/style.css (CSS variables) + site_parts.py (layout fragments).
Change the theme once; every page, past and future, follows it.
"""
import html as html_mod
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import site_parts

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
OUT = REPO / "_site"

# ---- templates ---------------------------------------------------------------

LANDING_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>{title}</h1>
      <div class="threat-line {threat_class}">Overall Daily Threat Level: {threat_level}.</div>
    </section>

    <div class="briefing-body">
{body}
    </div>

    <p class="muted" style="margin-top:32px;"><a href="history.html">← View past briefings (History)</a></p>
  </main>
{footer}
</body>
</html>
"""

BRIEFING_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <a href="../history.html" class="back">← All briefings</a>
      <h1>{title}</h1>
      <div class="threat-line {threat_class}">Overall Daily Threat Level: {threat_level}.</div>
    </section>

    <div class="briefing-body">
{body}
    </div>
  </main>
{footer}
</body>
</html>
"""

HISTORY_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>History — Past Briefings</h1>
      <p style="color:var(--text-dim);">Every edition of the Daily Security Intelligence Briefing, newest first. The latest edition is always the landing page.</p>
    </section>

{months}
  </main>
{footer}
</body>
</html>
"""

MONTH_TEMPLATE = """    <section class="history-month">
      <h2>{month_label}</h2>
{weeks}
    </section>
"""

WEEK_TEMPLATE = """      <h3 class="history-week">{week_label}</h3>
      <ul class="history-list">
{items}
      </ul>
"""

MONTH_FLAT_TEMPLATE = """    <section class="history-month">
      <h2>{month_label}</h2>
      <ul class="history-list">
{items}
      </ul>
    </section>
"""

HISTORY_ITEM = """        <li><span class="date">{date_label}{latest_tag}</span> — <a href="briefings/{filename}">{title}</a> <span class="threat {threat_class}">{threat_level}</span></li>"""

ARTICLES_INDEX_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>Articles</h1>
      <p style="color:var(--text-dim);">Longer-form writing. Same theme, different format.</p>
    </section>

    <div class="briefings-list">
{cards}
    </div>
  </main>
{footer}
</body>
</html>
"""

ARTICLE_CARD = """      <div class="card">
        <div class="date">{date_label}</div>
        <h3><a href="articles/{filename}">{title}</a></h3>
      </div>
"""

ARTICLE_TEMPLATE = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <a href="../articles.html" class="back">← All articles</a>
      <h1>{title}</h1>
      <div class="meta muted">{date_label}</div>
    </section>

    <div class="briefing-body">
{body}
    </div>
  </main>
{footer}
</body>
</html>
"""

# ---- helpers -----------------------------------------------------------------

def threat_class(level: str) -> str:
    level = level.upper()
    if "CRITICAL" in level:
        return "threat-critical"
    if "HIGH" in level:
        return "threat-high"
    if "MODERATE" in level:
        return "threat-moderate"
    return "threat-low"


def extract_title_and_threat(raw: str, date_str: str) -> tuple:
    """Return (title, threat_level). Works for merged bodies, normalized bodies
    (with <!-- threat_level: X --> comment), and files missing both."""
    title = ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
    if m:
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    if not title:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            title = f"Daily Security Intelligence Briefing — {dt.strftime('%B %-d, %Y')}"
        except Exception:
            title = f"Daily Security Intelligence Briefing — {date_str}"
    threat = ""
    # 1) machine-readable comment (n8n contract)
    mt = re.search(r"<!--\s*threat_level:\s*([A-Za-z]+)\s*-->", raw)
    if not mt:
        # 2) inline text (merged Google-Docs bodies)
        mt = re.search(r"Overall Daily Threat Level:\s*([A-Z]+)", raw)
    if mt:
        threat = mt.group(1).upper()
    return title, threat


def clean_merged_body(raw: str) -> str:
    """Strip the Google-Docs inline styles + duplicated headers from a merged body."""
    body = raw
    # remove the outer title h1 (renderer supplies it) + Executive Threat Brief h1
    body = re.sub(r"<h1[^>]*>Daily Security Intelligence Briefing.*?</h1>", "", body, flags=re.S)
    body = re.sub(r"<h1[^>]*>Executive Threat Brief.*?</h1>", "", body, flags=re.S)
    # remove the threat-level paragraph (renderer supplies it)
    body = re.sub(r"<p[^>]*>Overall Daily Threat Level:.*?</p>", "", body, flags=re.S)
    # strip inline styles (nested-quote safe)
    body = re.sub(r'\s+style="[^"]*"', "", body)
    body = re.sub(r'<spanRoboto Mono["\']*>', "<span>", body)
    body = re.sub(r"<p>\s*</p>", "", body)
    return body.strip()


def normalize_tier_body(raw: str) -> str:
    """Normalized body already has .brief-summary/.tier/.tier-item — pass through
    (theme CSS styles them)."""
    return raw.strip()


def parse_date(date_str: str) -> datetime | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


# ---- history -----------------------------------------------------------------

def build_history(entries: list) -> str:
    """entries: list of dicts {date, filename, title, threat}. Group by month;
    current month gets week sub-groups, older months flat lists."""
    entries.sort(key=lambda e: e["date"], reverse=True)
    now = datetime.now()
    current_ym = now.strftime("%Y-%m")

    months: dict[str, list] = {}
    for e in entries:
        ym = e["date"][:7]
        months.setdefault(ym, []).append(e)

    sections = []
    for ym in sorted(months.keys(), reverse=True):
        dt = datetime.strptime(ym, "%Y-%m")
        month_label = dt.strftime("%B %Y")
        items = months[ym]
        if ym == current_ym:
            # group by week (Mon-based), newest week first
            weeks: dict[datetime, list] = {}
            for e in items:
                d = parse_date(e["date"])
                if d is None:
                    continue
                monday = d - timedelta(days=d.weekday())
                weeks.setdefault(monday, []).append(e)
            week_blocks = []
            for monday in sorted(weeks.keys(), reverse=True):
                sunday = monday + timedelta(days=6)
                week_label = f"Week of {monday.strftime('%b %-d')}"
                if sunday.month != monday.month:
                    week_label += f" – {sunday.strftime('%b %-d')}"
                rows = [render_history_item(e, is_latest=(e is items[0] and ym == current_ym and monday == max(weeks.keys()))) for e in sorted(weeks[monday], key=lambda x: x["date"], reverse=True)]
                week_blocks.append(WEEK_TEMPLATE.format(week_label=week_label, items="\n".join(rows)))
            sections.append(MONTH_TEMPLATE.format(month_label=month_label, weeks="\n".join(week_blocks)))
        else:
            rows = [render_history_item(e, is_latest=False) for e in items]
            sections.append(MONTH_FLAT_TEMPLATE.format(month_label=month_label, items="\n".join(rows)))
    return "\n".join(sections)


def render_history_item(e: dict, is_latest: bool) -> str:
    latest_tag = " · LATEST" if is_latest else ""
    try:
        date_label = datetime.strptime(e["date"], "%Y-%m-%d").strftime("%b %-d, %Y")
    except Exception:
        date_label = e["date"]
    tc = threat_class(e.get("threat", ""))
    return HISTORY_ITEM.format(
        date_label=date_label,
        latest_tag=latest_tag,
        filename=e["filename"],
        title=e["title"],
        threat_class=tc,
        threat_level=e.get("threat", ""),
    )


# ---- feed --------------------------------------------------------------------

def build_feed(entries: list) -> str:
    entries.sort(key=lambda e: e["date"], reverse=True)
    items = []
    for e in entries:
        dt = parse_date(e["date"])
        pub = dt.strftime("%a, %d %b %Y 00:00:00 +0000") if dt else ""
        link = f"https://bahansenus.github.io/web/briefings/{e['filename']}"
        items.append(f"""    <item>
      <title>{html_mod.escape(e['title'])}</title>
      <link>{link}</link>
      <guid>{link}</guid>
      <pubDate>{pub}</pubDate>
      <description>{html_mod.escape(e.get('excerpt', ''))}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>bahansen.us — Daily Security Intelligence Briefing</title>
    <link>https://bahansenus.github.io/web/</link>
    <description>The Daily Security Intelligence Briefing from bahansen.us — tiered security intelligence for busy operators.</description>
    <atom:link href="https://bahansenus.github.io/web/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""


# ---- main --------------------------------------------------------------------

def render_briefing(date_str: str, raw: str, entries_meta: list) -> None:
    title, threat = extract_title_and_threat(raw, date_str)
    if "<span" in raw and "tier-item" not in raw:
        body = clean_merged_body(raw)
        # merged body: wrap in .merged for the scoped theme styles
        body = f'<div class="merged">\n{body}\n    </div>'
        summary = extract_summary(raw)
    else:
        body = normalize_tier_body(raw)
        summary = ""
    excerpt = (summary or title)[:150].replace('"', "")

    # briefing page (depth 1)
    page = BRIEFING_TEMPLATE.format(
        head=site_parts.head(title, excerpt, depth=1),
        nav=site_parts.nav(depth=1, active="history"),
        title=title,
        threat_class=threat_class(threat),
        threat_level=threat or "—",
        body=body,
        footer=site_parts.footer(depth=1),
    )
    out_dir = OUT / "briefings"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{date_str}.html").write_text(page)

    # landing page (depth 0) if latest
    if date_str == entries_meta[0]["date"]:
        landing = LANDING_TEMPLATE.format(
            head=site_parts.head(title, excerpt, depth=0),
            nav=site_parts.nav(depth=0),
            title=title,
            threat_class=threat_class(threat),
            threat_level=threat or "—",
            body=body,
            footer=site_parts.footer(depth=0),
        )
        (OUT / "index.html").write_text(landing)


def extract_summary(raw: str) -> str:
    m = re.search(r"Overall Daily Threat Level:\s*[A-Z]+\.", raw)
    if not m:
        return ""
    s = raw[m.end():]
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ")
    m2 = re.search(r"TIER 1:", s)
    if m2:
        s = s[:m2.start()]
    return re.sub(r"\s+", " ", s).strip()


def copy_static() -> None:
    shutil.copy(REPO / "assets" / "style.css", OUT / "assets" / "style.css")
    shutil.copy(REPO / "assets" / "logo.jpg", OUT / "assets" / "logo.jpg")
    shutil.copy(REPO / "BAHansen_Logo.jpeg", OUT / "BAHansen_Logo.jpeg")


def build_about() -> None:
    page = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>About</h1>
      <p style="color:var(--text-dim);">Who's behind bahansen.us and how the Daily Security Intelligence Briefing is made.</p>
    </section>

    <div class="briefing-body">
      <div class="brief">bahansen.us is the personal site of Brett Hansen — a daily security intelligence briefing, home lab notes, and security research.</div>

      <h2>The Daily Security Intelligence Briefing</h2>
      <p>Every morning a fresh security briefing is published, cut through the noise to the signal that matters for operators. It is organized into three tiers:</p>
      <ul class="tag-list">
        <li><span class="tag-label">Tier 1</span> Priority targets — must-read items with sector/world-scale impact (mass-exploited zero-days, cloud-identity breaks, nation-state critical infrastructure).</li>
        <li><span class="tag-label">Tier 2</span> Essential intelligence — the default home for vulnerability news, patch notes, write-ups, and analysis.</li>
        <li><span class="tag-label">Tier 3</span> Industry noise — funding news, market speculation, and aging follow-ups worth a skim.</li>
      </ul>
      <p>Each edition carries an <em>Overall Daily Threat Level</em> (Critical / High / Moderate / Low) and a one-to-two sentence threat-vector summary at the top.</p>

      <h2>How it's made</h2>
      <p>The briefing is generated by an automated pipeline: a research pass pulls the day's security news, deduplicates it against prior coverage, and classifies each item into the tier structure above. It's assembled and delivered daily.</p>

      <h2>This site</h2>
      <p>A static site served from GitHub Pages — fast, secure, no tracking, no cookies. The full archive lives under <a href="history.html">History</a>.</p>
    </div>
  </main>
{footer}
</body>
</html>
""".format(
        head=site_parts.head("About — bahansen.us",
                             "About bahansen.us and the Daily Security Intelligence Briefing.", depth=0),
        nav=site_parts.nav(depth=0, active="about"),
        footer=site_parts.footer(depth=0),
    )
    (OUT / "about.html").write_text(page)
    print("  about.html")


def build_privacy() -> None:
    page = """{head}
{nav}
  <main class="container">
    <section class="briefing-header">
      <h1>Privacy Policy</h1>
      <p style="color:var(--text-dim);"><em>Effective date: August 25, 2026</em></p>
    </section>

    <div class="briefing-body">
      <div class="brief">This site is a personal website operated by Brett Hansen. This page describes what information is collected and how it is used.</div>

      <h2>Information we collect</h2>
      <p>This site does not require accounts, does not use cookies for tracking, and does not sell or share personal data. Standard web server logs (IP address, user agent, requested page) may be collected for operational and security purposes and are retained only as long as needed.</p>

      <h2>Google API usage</h2>
      <p>This site's operator uses Google APIs (Gmail and Google Drive) to automate delivery of a personal newsletter. Access is limited to the scopes required for that automation (<code>gmail.send</code>, <code>drive</code>) and is used solely to send the newsletter to the account owner and read the briefing document that feeds it. No data is shared with third parties.</p>

      <h2>Hosting & third-party services</h2>
      <p>This site is hosted on GitHub Pages. GitHub may process standard request logs in accordance with its own privacy policy. If a custom domain is configured via Cloudflare, Cloudflare may act as a reverse proxy and process request metadata (IP address, user agent) under its privacy policy. Neither party receives personal data beyond standard request logs.</p>

      <h2>Contact</h2>
      <p>Questions about this policy can be directed to the site owner via the contact information available on the site.</p>
    </div>
  </main>
{footer}
</body>
</html>
""".format(
        head=site_parts.head("Privacy Policy — bahansen.us",
                             "Privacy policy for bahansen.us, the personal website of Brett Hansen.", depth=0),
        nav=site_parts.nav(depth=0, active="privacy"),
        footer=site_parts.footer(depth=0),
    )
    (OUT / "privacy.html").write_text(page)
    print("  privacy.html")


def main():
    # fresh output
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    copy_static()

    # gather briefing entries
    entries = []
    for f in sorted((CONTENT / "briefings").glob("*.html")):
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not date_m:
            continue
        date_str = date_m.group(1)
        raw = f.read_text()
        title, threat = extract_title_and_threat(raw, date_str)
        entries.append({"date": date_str, "filename": f.name, "title": title, "threat": threat})
    entries.sort(key=lambda e: e["date"], reverse=True)

    for e in entries:
        render_briefing(e["date"], (CONTENT / "briefings" / e["filename"]).read_text(), entries)
        print(f"  briefing {e['date']}: {e['title'][:50]}")

    # history
    history_html = HISTORY_TEMPLATE.format(
        head=site_parts.head("History — Past Briefings — bahansen.us",
                             "Archive of Daily Security Intelligence Briefings from bahansen.us.", depth=0),
        nav=site_parts.nav(depth=0, active="history"),
        months=build_history(entries),
        footer=site_parts.footer(depth=0),
    )
    (OUT / "history.html").write_text(history_html)
    print("  history.html")

    # feed
    (OUT / "feed.xml").write_text(build_feed(entries))
    print("  feed.xml")

    # articles scaffold
    articles = sorted((CONTENT / "articles").glob("*.html"))
    cards = []
    for a in articles:
        raw = a.read_text()
        m = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else a.stem
        md = re.search(r"(\d{4}-\d{2}-\d{2})", a.name)
        date_label = md.group(1) if md else ""
        cards.append(ARTICLE_CARD.format(date_label=date_label, filename=a.name, title=title))
        # article page
        page = ARTICLE_TEMPLATE.format(
            head=site_parts.head(title, title, depth=1),
            nav=site_parts.nav(depth=1, active="articles"),
            title=title,
            date_label=date_label,
            body=raw,
            footer=site_parts.footer(depth=1),
        )
        (OUT / "articles").mkdir(parents=True, exist_ok=True)
        (OUT / "articles" / a.name).write_text(page)
        print(f"  article {a.name}")
    articles_index = ARTICLES_INDEX_TEMPLATE.format(
        head=site_parts.head("Articles — bahansen.us", "Articles from bahansen.us.", depth=0),
        nav=site_parts.nav(depth=0, active="articles"),
        cards="\n".join(cards) if cards else "      <p class=\"muted\">No articles yet — coming soon.</p>",
        footer=site_parts.footer(depth=0),
    )
    (OUT / "articles.html").write_text(articles_index)
    print("  articles.html")

    # about + privacy
    build_about()
    build_privacy()

    print("DONE")


if __name__ == "__main__":
    main()
