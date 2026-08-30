#!/usr/bin/env python3
"""Convert a merged Google-Docs briefing HTML body into the canonical JSON
schema (docs/briefing-json-contract.md). Used to create test fixtures and as a
reference implementation for the n8n normalization Code node.

Usage:
  python3 scripts/html_to_json.py content/briefings/2026-08-30.html > /tmp/out.json
  python3 scripts/html_to_json.py content/briefings/2026-08-30.html --write
"""
import html as html_mod
import json
import re
import sys
from pathlib import Path


def decode(text: str) -> str:
    return html_mod.unescape(re.sub(r"<[^>]+>", "", text)).replace("\xa0", " ").strip()


def extract_item_title(tag_html: str) -> str:
    return decode(tag_html)


def parse_field_li(li_html: str) -> dict:
    """Parse a <li> into {label, value}. Label = first bold span (or before ':').
    Handles the Google-Docs span-wrapped structure."""
    # remove <ul>/<li> wrappers, keep inner
    m = re.search(r"<li[^>]*>(.*?)</li>", li_html, re.S)
    inner = m.group(1) if m else li_html
    # label = first <span> with font-weight:700, or text up to first ':' 
    label = ""
    bm = re.search(r'<span[^>]*font-weight:700[^>]*>(.*?)</span>', inner, re.S)
    if bm:
        label = decode(bm.group(1)).rstrip(":")
    else:
        tm = re.match(r"^([^:]{1,60}):", decode(inner))
        if tm:
            label = tm.group(1).strip()
    # value = rest after the label span
    value = ""
    if bm:
        after = inner[bm.end():]
        value = decode(after)
    else:
        tm = re.match(r"^[^:]{1,60}:\s*(.*)$", decode(inner), re.S)
        if tm:
            value = tm.group(1).strip()
        else:
            value = decode(inner)
    return {"label": label, "value": value}


def parse_tier_block(block: str) -> list:
    """Parse a tier's items. Each item = <h1>/<h2> title + following <ul><li> fields."""
    items = []
    # split into item segments: title tag then its <ul>s
    segs = re.split(r"(<h[12][^>]*>.*?</h[12]>)", block, flags=re.S)
    cur = None
    for seg in segs:
        if re.match(r"<h[12]", seg.strip()):
            if cur and (cur["fields"] or cur["title"]):
                items.append(cur)
            cur = {"title": extract_item_title(seg), "fields": []}
        elif seg.strip() and cur is not None:
            # find all <li> in this segment
            for li in re.findall(r"<li[^>]*>.*?</li>", seg, re.S):
                f = parse_field_li(li)
                if f["value"]:
                    cur["fields"].append(f)
    if cur and (cur["fields"] or cur["title"]):
        items.append(cur)
    return items


def parse_tier3(block: str) -> list:
    out = []
    # Format A: <li> bullets
    for li in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S):
        txt = decode(li)
        if txt:
            out.append({"text": txt})
    # Format B: Google-Docs <table> (Topic | Description | Source) — the doc
    # format drifts; join the cells of each row into one readable line.
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        cells = [decode(td) for td in tds]
        cells = [c for c in cells if c]
        if not cells:
            continue
        # skip header row (Topic / Release, Description / Impact, Source Reference)
        head = " ".join(cells).lower()
        if "topic" in head and ("description" in head or "source" in head):
            continue
        if len(cells) == 1:
            out.append({"text": cells[0]})
        else:
            joined = " — ".join(cells[:-1]) + (f" ({cells[-1]})" if cells[-1] else "")
            out.append({"text": joined})
    return out


def convert(body: str) -> dict:
    # title + threat from the raw merged body
    title = "Daily Security Intelligence Briefing"
    tm = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
    if tm:
        title = decode(tm.group(1))
    threat = ""
    mt = re.search(r"Overall Daily Threat Level:\s*([A-Za-z]+)", body)
    if mt:
        threat = mt.group(1).upper()
    # summary: between threat level and TIER 1 marker
    summary = ""
    tp = body.find("Overall Daily Threat Level:")
    if tp >= 0:
        t1 = body.find("TIER 1:", tp)
        seg = body[tp: t1 if t1 >= 0 else len(body)]
        m2 = re.search(r"Overall Daily Threat Level:\s*[A-Z]+\.?\s*", seg)
        if m2:
            seg = seg[m2.end():]
        summary = decode(seg)

    # split into tier blocks by the <p class="title"> markers
    tier_splits = re.split(r'(<p[^>]*class="title"[^>]*>.*?</p>)', body, flags=re.S)
    tiers = {"tier1": [], "tier2": [], "tier3": []}
    cur_tier = None
    for seg in tier_splits:
        m = re.search(r"TIER ([123])", seg)
        if m and "class=\"title\"" in seg:
            cur_tier = "tier" + m.group(1)
            continue
        if seg.strip() and cur_tier:
            if cur_tier == "tier3":
                tiers[cur_tier].extend(parse_tier3(seg))
            else:
                tiers[cur_tier].extend(parse_tier_block(seg))

    result = {
        "title": title,
        "threat_level": threat,
        "summary": summary,
        "tier1": tiers["tier1"],
        "tier2": tiers["tier2"],
        "tier3": tiers["tier3"],
    }
    return result


def main():
    src = Path(sys.argv[1])
    raw = src.read_text()
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.S)
    body = m.group(1) if m else raw
    result = convert(body)
    out = json.dumps(result, indent=2, ensure_ascii=False)
    if "--write" in sys.argv:
        out_path = src.with_suffix(".json")
        out_path.write_text(out + "\n")
        print(f"Wrote {out_path} ({len(out)} bytes)")
    else:
        print(out)


if __name__ == "__main__":
    main()
