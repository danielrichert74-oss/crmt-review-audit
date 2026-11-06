# America's Car-Mart Review Audit

A zero-cost-first, evidence-preserving project to audit public Google Maps reviews of America's Car-Mart dealerships. Initial scope: Oklahoma, Missouri, Texas and Kentucky. Greenville, Texas is the qualification pilot.

## Current status

The first hosted Gosom scraper experiment failed qualification: it captured only 1 one-star review against a point-in-time Google listing benchmark of 69. That output is not a comprehensive audit dataset.

A separate experimental Playwright collector now operates the rendered Google Maps interface:
- `tools/local_maps_collector.py`
- `requirements-local.txt`
- `LOCAL_BROWSER_PILOT.md`

This collector is **not yet live-tested**. It attempts to search for the exact dealership, open Reviews, select Lowest, scroll the visible review feed, and preserve raw review cards plus a trace manifest. It never declares completeness automatically. The next engineering gate is a live Greenville run that proves correct listing identity, successful Lowest sorting, real feed movement, accurate field extraction, and count reconciliation.

## Collection and evidence principles

1. Use the official America's Car-Mart location directory to establish each dealership's name, address and phone number.
2. Search Google Maps using the exact dealership identity and verify the business profile before collecting.
3. Select Google Reviews sorted by Lowest.
4. Preserve raw captures before deriving the one-star dataset.
5. Retain available review text, reviewer display name/profile, date, rating, review ID, listing URL, owner response and response date.
6. Record collection time, collector version, listing identity, scroll trace, counts, duplicates, stop reason and limitations.
7. Compare captured one-star records with a fresh Google per-rating benchmark and independently spot-check source records.
8. Mark coverage complete only after a defensible reconciliation. A successful process exit, stalled feed, or matching count alone is not sufficient proof of historical completeness.

## $0 guardrails

- No paid APIs, subscriptions, credits, proxies, card trials, automatic top-ups, or billing-enabling upgrades.
- Use free/open-source tools and free compute only where available.
- If a proposed service has uncertain charges, do not use it.
- Do not bypass sign-in, security controls, or access restrictions.
- No review aggregators as substitutes for Google's source listing.
- Treat review allegations as allegations; collection does not independently verify them.

## Greenville pilot

The official Car-Mart Greenville directory page supplies the dealership identity and address. Its directions link was observed resolving to an address-only Google Maps pin, not the canonical business profile. The visible-browser pilot therefore searches by exact name and address rather than assuming the directions URL is the review listing.

See [LOCAL_BROWSER_PILOT.md](LOCAL_BROWSER_PILOT.md) for setup and the experimental run command. That path currently requires a desktop/laptop with Python and Chromium; it is not an Android-installable app.

## Outputs

The local pilot writes:
- `output/local-browser-capture.jsonl`: raw visible review-card captures, including mixed ratings
- `output/local-browser-capture.manifest.json`: listing identity, collection metadata, scroll trace, counts and limitations

Do not submit these outputs as a comprehensive audit until the Greenville qualification gates pass. Expand to other dealerships only after the pilot is repeatable and independently verified.
