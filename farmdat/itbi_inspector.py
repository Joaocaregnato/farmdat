"""
ITBI Portal Inspector
---------------------
Run before writing any scraper to capture real endpoint structure.
Guides the user through browser DevTools inspection.

Usage:
    python -m farmdat.itbi_inspector --url https://prefsorriso-mt.agilicloud.com.br/portal/sorriso/
"""
import argparse


INSPECTION_GUIDE = """
=== ITBI Portal Inspection Guide ===

Target URL: {url}

STEP 1 — Open the portal and enable network capture:
  1. Navigate to: {url}
  2. Press F12 → select "Network" tab
  3. Check "Preserve log" and filter by "Fetch/XHR"

STEP 2 — Trigger a sample ITBI query:
  - Search for any property (use an address or property code)
  - Watch the Network tab for matching requests

STEP 3 — Find the data endpoint:
  Look for requests to URLs containing any of:
  - /api/, /ws/, /servicos/, /consulta, /imovel, /itbi, /transacao

STEP 4 — Extract the curl command:
  Right-click the request → "Copy" → "Copy as cURL"
  Save to: curl_captured.txt

STEP 5 — Implement the scraper:
  Create farmdat/scrapers/{municipio}_scraper.py implementing BaseScraper.

WHAT TO LOOK FOR:
  ✓ Request method: GET or POST?
  ✓ Payload/query params (what identifies the property?)
  ✓ Auth headers: Cookie, Authorization, X-CSRF-Token?
  ✓ Response format: JSON, HTML, XML?
  ✓ Pagination: is there a page/offset param?

ANTI-PATTERNS TO AVOID:
  ✗ Do NOT assume sequential numeric IDs exist
  ✗ Do NOT brute-force without confirming the ID pattern first
  ✗ Do NOT ignore rate limiting — always add delays between requests
"""


def main():
    parser = argparse.ArgumentParser(description="ITBI portal inspection guide")
    parser.add_argument(
        "--url",
        default="https://prefsorriso-mt.agilicloud.com.br/portal/sorriso/",
    )
    args = parser.parse_args()
    print(INSPECTION_GUIDE.format(url=args.url))


if __name__ == "__main__":
    main()
