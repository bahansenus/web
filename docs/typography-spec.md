# bahansen.us Typography & Theme Spec

The **single source of truth** for how the site looks. All values live in
`assets/style.css` (CSS variables + class rules). Change a value there → every
page, past and future, updates. **Never** hardcode colors/fonts/sizes per-page
or in content — the whole point of the template system.

## Fonts

| Role | Font | CSS var |
|------|------|---------|
| Body / headings / article titles | **Inter** | `--sans` |
| Technical accents (dates, threat level, tier markers, field labels, nav meta) | **JetBrains Mono** | `--mono` |

Loaded via Google Fonts `@import` at the top of `style.css`. No other fonts are
used anywhere. If Google's export mentions other fonts (Plus Jakarta Sans,
Poppins, Montserrat...), the build strips them — they never reach the rendered
page.

## Colors (CSS variables)

| Var | Value | Use |
|-----|-------|-----|
| `--bg` | `#0b1220` | page background (dark navy) |
| `--bg-soft` | `#111a2e` | cards, brief band, tier-header band |
| `--bg-card` | `#0f1830` | cards |
| `--border` | `#1f2b47` | borders |
| `--text` | `#e6eaf1` | headings, titles, primary text (soft off-white — NOT pure white, avoids eye strain) |
| `--text-dim` | `#d0d7e2` | body field text (soft gray-white) |
| `--accent` | `#38bdf8` | links, labels, borders (sky blue) |
| `--accent-2` | `#818cf8` | TIER section headers (indigo/violet) |
| `--danger` / `--warn` / `--ok` | `#f87171`/`#fbbf24`/`#34d399` | threat levels |

## Unified typography spec (all tiers, all formats)

| Element | Spec |
|---------|------|
| **Article titles** (Tier 1/2/3 — `<h1>`, `<h2>`, `.tier-item h3`) | `1.15rem` bold · Inter · `--text` · no border · `line-height 1.15` |
| **Body field values** ("Why You Must Read This", "Subject", "Domain", etc.) | `1rem` · Inter · `--text-dim` · `line-height 1.5` |
| **Field labels** ("Why You Must Read This:", "Source:", "Domain:") | `0.8rem` bold · JetBrains Mono · `--accent` |
| **TIER section headers** (`p.title` / `h2.tier`) | `1.5rem` bold · uppercase · JetBrains Mono · `--accent-2` · left accent border + `--bg-soft` band |
| **Executive summary** (`.brief-summary`) | `1.02rem` · `--text` · accent left border + `--bg-soft` band |

## CSS rules that enforce this

- `.briefing-body .merged h1`, `.briefing-body .merged h2`, `.tier-item h3` — all
  identical (the Google export uses `<h1>` for Tier 1 and `<h2>` for Tier 2;
  the theme normalizes both).
- `.briefing-body .merged p`, `.tier-item p` — body field values.
- `.briefing-body .merged ul li span:first-child`, `.tier-item .label` — field labels.
- `.briefing-body .merged p.title`, `.briefing-body h2.tier` — TIER section headers.

## History of format drift (why this spec exists)

- Google doc template has changed fonts repeatedly: Inter → Montserrat → Plus
  Jakarta Sans (with Poppins appearing in nested-quote style attrs).
- Tier headers are `p.title` wrapped in spans; article titles are `<h1>` (Tier 1)
  vs `<h2>` (Tier 2).
- Tier 3 content has appeared as `<li>` bullets AND as a `<table>`.
- The build (render.py) strips ALL inline styling + normalizes structure, so
  none of this drift affects the rendered site. The canonical JSON contract
  (docs/briefing-json-contract.md) makes the site fully independent of Google's
  HTML.

## Do not

- Don't put `style="..."` inline in content files (HTML briefings). The build
  strips them, but they're fragile (nested-quote bug) — use canonical JSON instead.
- Don't add a new font to the site without updating this spec + `--sans`/`--mono`.
- Don't hand-edit generated `_site/` pages.
