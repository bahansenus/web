# bahansen.us — Website

The public website for [bahansen.us](https://bahansen.us) — Brett Hansen's personal site featuring the **Daily Security Intelligence Briefing** archive, home lab documentation, and research.

## How it works (template-driven static site)

```
n8n newsletter  →  content/briefings/YYYY-MM-DD.html   (raw content, committed)
                     │
                     ▼  GitHub Actions (on push to main)
              scripts/build_site.py   (render.py + validate_links.py)
                     │
                     ▼
              _site/  →  deployed to GitHub Pages
```

- **Content lives in `content/`** — raw HTML bodies, one file per briefing/article.
  This is the archive; old files are never deleted, they just stop being the landing page.
- **The theme is `assets/style.css`** (colors, fonts, section styles as CSS variables)
  + `scripts/site_parts.py` (layout fragments: masthead, nav, footer).
  Change the theme once → every page, past and future, updates.
- **Pages are generated, never hand-edited** — `render.py` produces:
  - `index.html` = latest briefing (the landing page / "front page")
  - `briefings/YYYY-MM-DD.html` = one page per edition
  - `history.html` = archive grouped by month, current month by week
  - `feed.xml` = RSS for subscribers
  - `articles.html` + `articles/*` = long-form section (scaffold)
  - `about.html`, `privacy.html`

## Structure

```
.
├── content/
│   ├── briefings/           # raw HTML body per edition (n8n push target)
│   │   ├── 2026-08-28.html  # merged Google-Docs export
│   │   └── 2026-07-28.html  # normalized tier body
│   └── articles/            # future long-form (same theme)
├── assets/
│   ├── style.css            # THE THEME — colors, fonts, layout styles
│   └── logo.jpg             # optimized logo (BAHansen_Logo.jpeg is the master)
├── scripts/
│   ├── render.py            # reads content/ → renders _site/
│   ├── validate_links.py    # link checker (fails build on broken links)
│   ├── build_site.py        # one-command: render + validate
│   ├── site_parts.py        # shared layout fragments (masthead/nav/footer)
│   └── migrate_content.py   # one-time: seeded content/ from old sources
├── docs/
│   └── n8n-push-recipe.md   # n8n → GitHub Contents API push recipe
├── .github/workflows/deploy.yml  # build + deploy pipeline
└── _site/                   # generated output (gitignored)
```

## Development / local build

```bash
python3 scripts/build_site.py     # renders _site/ + validates links
python3 -m http.server 8000 -d _site   # preview at http://localhost:8000
```

## Adding a new briefing (manual)

1. Get today's merged HTML body (from the n8n newsletter / Drive export).
2. Save it to `content/briefings/YYYY-MM-DD.html` (optionally with
   `<!-- threat_level: X -->` at the top).
3. `python3 scripts/build_site.py` (or just commit — Actions builds).
4. Commit + push. The build renders the landing page, archives the old one,
   updates History + RSS, and deploys.

## Adding an article

Same pattern: save the body to `content/articles/<slug>.html` with an `<h1>`,
commit, push. It appears under Articles with the same theme.

## Deployment

Push to `main` — GitHub Actions runs `scripts/build_site.py`, validates links,
and deploys `_site/` to GitHub Pages.

## Notes

- Push credentials: Bitwarden secret `GITHUB_WEB_KEY` (Home Lab project).
- The `briefings/` folder in the repo root is legacy (pre-refactor rendered
  output); the authoritative source is now `content/` and the generated `_site/`.
- Custom domain (bahansen.us) via Cloudflare is still pending — the relative
  path scheme means it will work at the root with no code change.
