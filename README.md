# America's Car-Mart Review Audit

A zero-cost-first, evidence-preserving collector for public Google Maps reviews of America's Car-Mart dealerships. The initial pilot is Greenville, Texas; planned states are Oklahoma, Missouri, Texas, and Kentucky.

## Collection rules

- Use each dealership's official America's Car-Mart location page to establish the business and its Google Maps listing.
- Query the listing's Google Maps Place ID through Stophy's public Google Maps Reviews API.
- Request reviews sorted by `lowest`, then retain **only rating = 1** in the audit dataset.
- Follow every returned cursor until pagination ends or an explicit limit/error occurs.
- Preserve the raw API response, review text, author display name, publication date, review URL, owner response and response date, place ID, listing URL, page number, cursor status, and collection timestamp.
- Do not use review aggregators.
- Never describe a location as complete unless pagination ended normally and the run log records the number of pages and records.
- Keep allegations as allegations; collection is not verification of the reviewer's claims.

## Cost and safety

- No paid services, paid credits, card trials, or automatic top-ups.
- Workflow is manual-dispatch only. It does not run on a schedule.
- Stophy's first page can be requested without an API key according to its documentation. Later pages require a Stophy API key and consume the account's existing free credits. Never put a key in source code; add it only as the GitHub Actions secret `STOPHY_API_KEY`.
- The workflow has a configurable page cap. Start with one page for the pilot. Increase only after reviewing the first-page output and confirming free credits are available.
- Do not commit collected review data to the repository; the workflow uploads it as a private Actions artifact instead.

## Pilot setup

1. Confirm the exact Greenville, TX America's Car-Mart location page and its Google Maps listing.
2. Obtain the Google Maps Place ID from that listing (do not substitute a similarly named dealership).
3. In GitHub Actions, run **Greenville pilot - Stophy reviews** manually with the Place ID, listing URL, and `max_pages=1`.
4. Inspect the JSON/CSV and run log. Only then consider further pagination.
5. Add `STOPHY_API_KEY` as a repository Actions secret only if the first page confirms the correct listing and additional pages are needed.

## Local run

Requires Python 3.11+ and `requests`.

```bash
python -m pip install requests
export STOPHY_PLACE_ID="YOUR_VERIFIED_PLACE_ID"
export STOPHY_LISTING_URL="YOUR_VERIFIED_GOOGLE_MAPS_URL"
export STOPHY_MAX_PAGES=1
python src/collect_reviews.py
```

## Output

The collector writes:
- `output/reviews.jsonl`: one JSON object per one-star review
- `output/reviews.csv`: tabular one-star records
- `output/run_manifest.json`: page counts, errors, pagination status, and audit limitations

A run that stops at a configured page cap is marked **incomplete** even if it returns reviews.
