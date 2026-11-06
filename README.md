# America's Car-Mart Review Audit

A zero-cost-first, evidence-preserving collector for public Google Maps reviews of America's Car-Mart dealerships. Scope: Oklahoma, Missouri, Texas and Kentucky. Greenville, Texas is the pilot.

## Current collection design

The primary pilot now uses the open-source [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper), not Stophy or TinyFish.

1. Read the Greenville dealership's official Google Maps listing URL from `data/dealerships.csv`.
2. Pass that exact listing URL directly to the scraper. The upstream project explicitly supports Google Maps place URLs as input, avoiding broad business searches.
3. Request extended review extraction (upstream documents approximately 300 reviews per place).
4. Verify the returned business against Greenville's phone number, or its business name and street address.
5. Retain only records with a one-star rating. Non-one-star reviews are discarded from the audit outputs.
6. Preserve review text, reviewer name/profile, date, review ID, listing URL, and owner response/date when present.
7. Compare the captured one-star count with Google's per-rating count and mark completeness only when the counts match.

## $0 guardrails

- The scraper is MIT-licensed open-source software and runs on a GitHub-hosted Actions runner.
- No paid services, paid credits, card trials, or automatic top-ups.
- No proxy purchase, paid API, or secret key is configured.
- The workflow is manual / test-triggered only; it is not scheduled.
- Raw mixed-rating scraper output is removed after filtering. The uploaded artifact contains only the one-star audit records and the manifest.
- Upstream extraction is documented as up to approximately 300 reviews per place. If the captured one-star count does not match Google's per-rating count, the manifest marks coverage incomplete.
- The upstream review schema does not currently expose an individual review permalink; review ID and reviewer profile URL are retained instead.
- Do not use review aggregators. Treat allegations as allegations; collection does not independently verify them.

## Run

Open the repository's **Actions** tab and select **Greenville pilot - gosom Google Maps scraper**. Run it manually. No secrets or paid services are required.

## Output

- `output/reviews.jsonl`: one record per verified one-star review
- `output/reviews.csv`: tabular one-star records
- `output/run_manifest.json`: listing identity, source counts, captured counts, completeness assessment and limitations

Do not claim comprehensive coverage until the manifest confirms the captured one-star count matches Google's per-rating listing count. Expand to other dealerships only after the Greenville pilot passes verification.
