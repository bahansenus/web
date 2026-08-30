# n8n → Website Push (GitHub Contents API)

How the n8n newsletter workflow publishes today's briefing to the bahansen.us
website. The workflow pushes ONE canonical JSON file; GitHub Actions renders the
site and deploys it.

## Flow

```
[Daily Newsletter workflow finishes — Generate (Gemini) structured JSON in memory]
  → Prep website push (Code): normalize nl → canonical contract → base64
  → HTTP Request node: PUT /repos/bahansenus/web/contents/content/briefings/YYYY-MM-DD.json
      headers: Authorization: token ***
      body:    { "message": "feat(newsletter): push briefing YYYY-MM-DD",
                 "content": "<base64 of canonical JSON string>",
                 "sha": "<existing file sha, if updating>" }
  → git push to main (the API commits directly)
  → GitHub Actions: build_site.py renders → validates → deploys _site/
  → https://bahansenus.github.io/web/ updates automatically
```

Since v4.0 (2026-08-30) the pushed artifact is **canonical JSON, not HTML** —
pure data (title, threat_level, summary, tier1/2/3 with label/value fields).
The site's own theme renders it; Google's fonts/sizes/structure never touch the
site. Schema: `docs/briefing-json-contract.md`. Reference normalization:
`scripts/html_to_json.py`.

## Credential (n8n)

- Name: `GitHub Web Key` (type: `Header Auth`)
- Header: `Authorization`
- Value: `token <GITHUB_WEB_KEY from Bitwarden>`
  - GITHUB_WEB_KEY is secret id `86bdfa75-7f65-4240-b80f-b4b40145874a` in the
    Home Lab Bitwarden project. Its `.value` field **IS the token directly** — a
    fine-grained PAT, prefix `github_pat_`, 93 chars. NOT nested JSON.
  - n8n note: n8n container mounts only `./data:/home/node/.n8n` — no
    `/opt/data/.env`. Add the credential via the n8n UI (or a one-off
    credentials API call from Hermes). Do NOT store the raw token in the
    workflow; reference the credential.

## HTTP Request node config

- Method: **PUT**
- URL: `https://api.github.com/repos/bahansenus/web/contents/content/briefings/{{$now.toFormat('yyyy-MM-dd')}}.json`
- Authentication: `Generic Credential Type` → `GitHub Web Key` (Header Auth)
- Body (JSON):
  ```json
  {
    "message": "feat(newsletter): push briefing {{$now.toFormat('yyyy-MM-dd')}}",
    "content": "{{ $json['content'] }}",
    "sha": "{{ $json['existingSha'] }}"
  }
  ```
  - `content`: base64 of the **canonical JSON string** (produced by the `Prep
    website push` Code node from `$('Parse newsletter').first().json.nl`).
  - `existingSha`: only needed when the file already exists (re-push/update). Get
    it from `GET /repos/bahansenus/web/contents/content/briefings/YYYY-MM-DD.json`
    first, or omit for first push (GitHub returns 201; a second push needs sha).

## Content file contract

The pushed file at `content/briefings/YYYY-MM-DD.json` is **canonical data**:

```json
{
  "date": "2026-08-30",
  "title": "Daily Security Intelligence Briefing — August 30, 2026",
  "threat_level": "CRITICAL",
  "summary": "executive brief, plain text",
  "tier1": [{ "title": "1. ...", "fields": [{ "label": "...", "value": "..." }] }],
  "tier2": [...],
  "tier3": [{ "text": "..." }]
}
```

Legacy `.html` briefings (07-28 → 08-29) remain supported by the renderer;
`.json` supersedes `.html` for the same date. New pushes are always `.json`.

## Verification

After the workflow fires:

1. Check the commit landed: `GET https://api.github.com/repos/bahansenus/web/commits?path=content/briefings/`
2. Check Actions: `GET https://api.github.com/repos/bahansenus/web/actions/runs`
   — the `build` job must succeed (it runs `scripts/build_site.py`).
3. Check live:
   - `GET https://bahansenus.github.io/web/` → title = today's briefing
   - `GET https://bahansenus.github.io/web/history.html` → new entry at top
   - `GET https://bahansenus.github.io/web/feed.xml` → new `<item>`

## Failure modes

- **404 on contents URL** → file path wrong or repo name wrong (`bahansenus/web`).
- **403/401** → token missing/expired/rotated. Re-fetch GITHUB_WEB_KEY from
  Bitwarden, update the n8n credential.
- **422 "sha doesn't match"** → the file already exists; fetch its current sha
  and include it in the PUT body.
- **Build fails in Actions** → run `python3 scripts/build_site.py` locally,
  check `scripts/validate_links.py` output; likely a content format issue.

## Notes

- The old approach (Hermes pushes via `push_website_github.sh`) still works for
  manual pushes. n8n uses the API directly so it doesn't need git/SSH.
- History, feed.xml, and the landing page all regenerate automatically from the
  content folder — no manual page edits after a push.
- For future "Articles": push to `content/articles/<slug>.html` the same way.
