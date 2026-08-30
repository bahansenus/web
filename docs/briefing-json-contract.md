# Canonical Briefing JSON — the "content as data" contract

The Daily Security Intelligence Briefing is stored as **pure data** (no HTML, no
formatting, no structure quirks). Both the website and (optionally) the email
render from this single canonical artifact. Google's fonts/sizes/structure NEVER
touch the rendered site — they're normalized away at the source.

## Why

- Google changes the doc template constantly (Inter → Montserrat → Plus Jakarta
  Sans; `<h1>` vs `<h2>` for titles; `class="title"` wrappers). The old process
  pushed Google's HTML and the build had to strip it — fragile.
- This contract makes the site a pure template engine: it renders whatever data
  it's given, using the site's own fixed templates. Google can change everything
  and the site never moves (only the n8n normalization node may need a tweak).
- The JSON is also the durable backup / rebuild source in local git.

## Location

- Website repo: `content/briefings/YYYY-MM-DD.json`
- Local backup: `/opt/data/git/homelab/data/newsletters/YYYY-MM-DD.json`

## Schema

```json
{
  "date": "2026-08-30",
  "title": "Daily Security Intelligence Briefing — August 30, 2026",
  "threat_level": "CRITICAL",
  "summary": "Primary threat vectors include ... (plain text, no markup)",
  "tier1": [
    {
      "title": "1. Anthropic Model Hardware Standard...",
      "fields": [
        { "label": "Source & Article Link", "value": "Ubiquiti Security Advisory / TLDR InfoSec" },
        { "label": "Technical Severity / Domain", "value": "Network / Critical (CVSS 10.0)" },
        { "label": "Why You Must Read This", "value": "..." },
        { "label": "Recommended Immediate Action", "value": "..." }
      ]
    }
  ],
  "tier2": [
    {
      "title": "1. Top AI Labs Warn...",
      "fields": [
        { "label": "Domain", "value": "..." },
        { "label": "Subject / Topic Summary", "value": "..." },
        { "label": "Key Technical & Strategic Takeaways", "value": "..." },
        { "label": "Essential Direct Quote", "value": "..." },
        { "label": "Source", "value": "..." }
      ]
    }
  ],
  "tier3": [
    { "text": "Nvidia in Talks to Acquire Hugging Face for ~$13B (TLDR Tech)" }
  ]
}
```

## Field rules

- `summary` — the executive threat brief, plain text only (HTML entities decoded).
- `tier1[]` / `tier2[]` — item `title` + `fields[]` as label/value pairs. Values
  are plain text; URLs are kept inside the text where the source put them
  (optionally also as `"url"` on the item for link-rich rendering).
- `tier3[]` — one `{ "text": ... }` per bullet, plain text.
- `threat_level` — one of `CRITICAL | HIGH | MODERATE | LOW`.
- All text is decoded from HTML entities (`&amp;` → `&`, `&nbsp;` → space, etc.).
  No HTML tags, no inline styles, no font names, no structure.

## How it's produced (n8n)

After the Generate (Gemini) node returns its structured JSON, the **Prep website
push** Code node:
1. Takes the parsed newsletter JSON (`execBrief`, `tier1[]`, `tier2[]`, `tier3[]`).
2. Normalizes it into this schema (plain text, label/value fields, entities decoded).
3. Outputs `{ json: { filename: "YYYY-MM-DD.json", content: <canonical JSON string> } }`.

The push node then PUTs that JSON to
`/repos/bahansenus/web/contents/content/briefings/YYYY-MM-DD.json` (Contents API,
same `GitHub Web Key` credential as the HTML push). The website build renders it.

## Backward compatibility

The renderer supports BOTH:
- `content/briefings/YYYY-MM-DD.html` (legacy — the 14 existing editions, kept as-is)
- `content/briefings/YYYY-MM-DD.json` (canonical — all new editions)

If a date has both, the `.json` wins. New pushes should be `.json`.
