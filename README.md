# America's Car-Mart Review Audit

A zero-cost-first, evidence-preserving collector for public Google Maps reviews of America's Car-Mart dealerships. Scope: Oklahoma, Missouri, Texas and Kentucky. Greenville, Texas is the pilot.

## Current pilot design

The GitHub Actions workflow automatically:
1. Searches Google Maps through Stophy for America's Car-Mart in Greenville, TX.
2. Matches the listing against the official dealership details (name/location and phone 903-458-9900).
3. Stops without requesting reviews unless exactly one candidate matches.
4. Requests the first reviews page sorted by lowest and locally retains only rating = 1.
5. Saves review text, reviewer, date, review URL, owner reply/date, resolved listing details, and a run manifest as a GitHub Actions artifact.

No Place ID needs to be manually supplied. No TinyFish or Google API key is used.

## $0 guardrails

- No paid services, paid credits, card trials, or automatic top-ups.
- The workflow makes only the first-page keyless Stophy Maps Search call and first-page keyless Reviews call for the pilot. Both are documented as free within Stophy's no-key daily limit. It does not paginate.
- Additional pages require a Stophy API key and consume credits. Do not add a key or increase page count without an explicit decision to do so.
- The workflow is not scheduled. It can be run manually from GitHub Actions; a change to `data/run-pilot.txt` is also configured as a one-time push trigger.
- Do not commit collected review data to the repository; output is uploaded as an Actions artifact.
- Do not use review aggregators. Keep allegations as allegations; collection does not verify claims.

## Run

Open the repository's **Actions** tab and select **Greenville pilot - Stophy reviews**. If GitHub asks to enable Actions, enable it, then run the workflow. No inputs or secrets are required for the first-page pilot.

## Output

- `output/reviews.jsonl`: one record per one-star review
- `output/reviews.csv`: tabular one-star records
- `output/run_manifest.json`: resolved listing, page counts, errors, pagination status and limitations

A one-page run is explicitly incomplete if Stophy returns a cursor. Do not claim comprehensive coverage until all pages are collected and the manifest confirms pagination exhaustion.
