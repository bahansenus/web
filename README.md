# bahansen.us — Website

The public website for [bahansen.us](https://bahansen.us) — Brett Hansen's personal site featuring the **Daily Security Intelligence Briefing** archive, home lab documentation, and research.

## Stack

- **Static HTML/CSS** — no build step, no framework. Fast and dependency-free.
- **Hosting:** GitHub Pages (repo `bahansenus/web`, deployed via GitHub Actions)
- **CDN/DNS:** Cloudflare (pending — custom domain `bahansen.us` TBD)
- **Content:** Daily briefings converted from the n8n newsletter pipeline output

## Structure

```
.
├── index.html               # Homepage
├── privacy.html             # Privacy policy (Google OAuth branding requirement)
├── briefings/
│   ├── index.html           # Archive index
│   └── YYYY-MM-DD.html      # One page per daily briefing
├── assets/
│   └── style.css            # Shared stylesheet
├── scripts/
│   ├── convert_briefings.py       # txt → HTML briefing pages
│   └── convert_merged_latest.py   # latest merged HTML → briefing page
└── .github/workflows/
    └── deploy.yml           # GitHub Pages deployment
```

## Deployment

Push to `main` — the GitHub Actions workflow automatically builds and deploys to GitHub Pages.

```bash
git push origin main
```

## Adding new briefings

1. Run `python3 scripts/convert_briefings.py` to regenerate all dated briefings from `/opt/data/docs/newsletters/`.
2. Run `python3 scripts/convert_merged_latest.py` to pull the latest merged briefing.
3. Update the threat level / excerpts in `index.html` and `briefings/index.html` if needed.
4. Commit and push.

## Notes

- The GitHub repo `bahansenus/web` was created 2026-08-28. Push credentials come from Bitwarden secret `GITHUB_WEB_KEY` (the Bahansen Lab BWS project).
- The original placeholder pages (simple home + privacy for Google OAuth branding) were replaced by this full site on 2026-08-28.
