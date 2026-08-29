#!/usr/bin/env python3
"""One-time migration: seed content/briefings/ from the current sources.

- 2026-08-28: extracts the raw <body> from merged-v37-verified HTML (the exact
  artifact the n8n pipeline produces — this is the contract for future pushes).
- Others: converts each txt briefing into a normalized raw HTML body using the
  same structure the renderer displays (title, threat, summary, tier sections).

The content files are the ARCHIVE + the n8n write target. Rendered pages are
generated from these by build_site.py.
"""
import html as html_mod
import re
from pathlib import Path

SRC_NEWSLETTERS = Path("/opt/data/docs/newsletters")
OUT = Path("/opt/data/git/website/content/briefings")

# --- merged HTML body (08-28) ------------------------------------------------
def extract_merged_body():
    src = SRC_NEWSLETTERS / "merged-v37-verified-2026-08-28.html"
    raw = src.read_text()
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.S)
    if not m:
        raise SystemExit("no <body> in merged HTML")
    body = m.group(1).strip()
    out = OUT / "2026-08-28.html"
    out.write_text(body + "\n")
    print(f"  {out.name}: {len(body)} bytes (raw merged body)")

# --- txt briefings -> normalized raw HTML body --------------------------------
def txt_to_raw_html(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = [l.rstrip() for l in text.split("\n")]

    title = lines[0].strip() if lines else ""
    # threat level
    threat = ""
    for l in lines[1:6]:
        if "Overall Daily Threat Level" in l:
            mt = re.search(r"Overall Daily Threat Level:\s*([A-Za-z]+)", l)
            if mt:
                threat = mt.group(1)
            break

    tier_idx = {"t1": -1, "t2": -1, "t3": -1}
    for i, l in enumerate(lines):
        if "TIER 1:" in l and tier_idx["t1"] < 0:
            tier_idx["t1"] = i
        elif "TIER 2:" in l and tier_idx["t2"] < 0:
            tier_idx["t2"] = i
        elif "TIER 3:" in l and tier_idx["t3"] < 0:
            tier_idx["t3"] = i

    # summary
    t1_start = tier_idx["t1"] if tier_idx["t1"] >= 0 else len(lines)
    summary_lines = [l.strip() for l in lines[3:t1_start] if l.strip() and "TIER" not in l]
    summary = " ".join(summary_lines)

    def block(start, end):
        if start < 0:
            return []
        return [l.strip() for l in lines[start + 1:end] if l.strip()]

    t1 = block(tier_idx["t1"], tier_idx["t2"] if tier_idx["t2"] >= 0 else tier_idx["t3"] if tier_idx["t3"] >= 0 else len(lines))
    t2 = block(tier_idx["t2"], tier_idx["t3"] if tier_idx["t3"] >= 0 else len(lines))
    t3 = block(tier_idx["t3"], len(lines))

    def render_items(block_lines):
        items = []
        cur = None
        for line in block_lines:
            if re.match(r"^\d+\.\s", line):
                if cur:
                    items.append(cur)
                cur = {"title": line, "fields": []}
            elif line.startswith("*") and cur is not None:
                cur["fields"].append(line.lstrip("* ").strip())
            else:
                if cur is not None:
                    if cur["fields"]:
                        cur["fields"][-1] += " " + line
                    else:
                        cur["title"] += " " + line
        if cur:
            items.append(cur)
        out = []
        for it in items:
            out.append(f'<div class="tier-item"><h3>{html_mod.escape(it["title"])}</h3>')
            for f in it["fields"]:
                m = re.match(r"^([^:]+):\s*(.*)$", f, re.S)
                if m:
                    out.append(f'<p><span class="label">{html_mod.escape(m.group(1))}:</span> {html_mod.escape(m.group(2))}</p>')
                else:
                    out.append(f"<p>{html_mod.escape(f)}</p>")
            out.append("</div>")
        return "\n".join(out)

    def render_t3(block_lines):
        out = ['<div class="tier-item"><h3>Tier 3 — Industry Noise &amp; Awareness Only</h3>']
        for line in block_lines:
            line = line.lstrip("* ").strip()
            if line:
                out.append(f"<p>• {html_mod.escape(line)}</p>")
        out.append("</div>")
        return "\n".join(out)

    parts = []
    # machine-readable threat level (contract for n8n content pushes)
    parts.append(f"<!-- threat_level: {threat} -->")
    parts.append(f'<div class="brief-summary">{html_mod.escape(summary)}</div>')
    if t1:
        parts.append('<h2 class="tier">Tier 1 — Priority Targets (Must-Read)</h2>')
        parts.append(render_items(t1))
    if t2:
        parts.append('<h2 class="tier">Tier 2 — Essential Intelligence (Summaries &amp; Analysis)</h2>')
        parts.append(render_items(t2))
    if t3:
        parts.append(render_t3(t3))
    return "\n".join(parts)


def migrate_txt():
    for f in sorted(SRC_NEWSLETTERS.glob("Daily Security Intelligence Briefing - *.txt")):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        if not m:
            continue
        date = m.group(1)
        raw = txt_to_raw_html(f.read_text())
        out = OUT / f"{date}.html"
        out.write_text(raw + "\n")
        print(f"  {out.name}: {len(raw)} bytes (normalized from txt)")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    extract_merged_body()
    migrate_txt()
    print("done")


if __name__ == "__main__":
    main()
