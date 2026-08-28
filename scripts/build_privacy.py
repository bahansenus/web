#!/usr/bin/env python3
"""Generate the Privacy page for bahansen.us (root depth)."""
from pathlib import Path

import site_parts

OUT = Path("/opt/data/git/website/privacy.html")

PAGE = """{head}
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
"""


def main():
    page = PAGE.format(
        head=site_parts.head("Privacy Policy — bahansen.us",
                             "Privacy policy for bahansen.us, the personal website of Brett Hansen.", depth=0),
        nav=site_parts.nav(depth=0, active="privacy"),
        footer=site_parts.footer(depth=0),
    )
    OUT.write_text(page)
    print(f"Wrote {OUT} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
