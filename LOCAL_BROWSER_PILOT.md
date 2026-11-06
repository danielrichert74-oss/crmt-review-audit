# Local visible-browser pilot (experimental)

This is a second collection path, separate from the failed GitHub-hosted Gosom run.
It uses Playwright to operate a normal Chromium browser against the public Google
Maps interface. It does not call private RPC endpoints, use proxies, or bypass
sign-in/security controls.

## Why this exists

The hosted runner test retrieved only 5 cards (1 one-star) against a listing
benchmark of 69 one-star reviews. That result is not usable as a complete audit.
A local browser session may encounter a different access path, but it must prove
that it is actually expanding the review list.

## Install

Python 3.10+ is required.

\`\`\`bash
python -m pip install -r requirements-local.txt
python -m playwright install chromium
\`\`\`

## Run Greenville pilot

\`\`\`bash
python tools/local_maps_collector.py --query "CAR-MART of Greenville, 5107 Interstate Highway 30, Greenville, TX 75402" --headed
\`\`\`

The visible browser is intentional for the first pilot: observe that the correct
business listing opens, the Reviews panel opens, and Lowest sorting is selected.
If any of those checks fail, the run must not be treated as a successful audit.

Outputs:
- \`output/local-browser-capture.jsonl\`: raw visible review-card captures (mixed ratings)
- \`output/local-browser-capture.manifest.json\`: run metadata and scroll trace

The raw file is deliberately retained for evidence/debugging. Filter one-star
records only in a downstream derived file; do not destroy the original capture.

## Current limitations

- Google Maps changes its interface; selectors may need adjustment.
- The collector is experimental. It now fails closed unless title, address,
  and phone match the expected Greenville business, and unless Lowest exposes
  an explicit selected-state signal. Inspect the visible browser during the pilot.
- It attempts to expand card-local "More" controls, but Google may still expose
  truncated review text or omit owner-response dates.
- Google may virtualize review cards, limit access, or stop loading older reviews.
- The script never marks a run complete. A stalled scroll is not proof of
  end-of-list, and a count comparison is still required.
- Review cards may omit fields; missing values remain blank rather than inferred.
- This path requires a desktop/laptop with Python and Chromium. It is not a
  phone-installable app and does not run silently in the background.

Do not submit this output as a comprehensive audit until a separate verifier
reconciles the count and independently spot-checks source records.


## Identity verification and one-star derivation

The Greenville run requires all of these visible-page checks before it opens
Reviews: profile title contains CAR-MART and Greenville; page text contains
the expected address tokens; and the expected phone digits are present.
The default expected values are the Greenville address and 903-458-9900.
Override them only when deliberately testing another independently verified
dealership.

After the raw capture, derive a one-star working file without changing the raw
evidence:

```bash
python tools/filter_one_star.py --input output/local-browser-capture.jsonl
```

This creates a one-star JSONL file, CSV export, and derivation manifest.
Unknown ratings and malformed input lines are counted separately. The derived
manifest remains explicitly incomplete because a filter cannot prove that
Google exposed every historical review.
