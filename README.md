# America's Car-Mart Review Audit

A zero-cost-first, evidence-preserving project to audit public Google Maps reviews of America's Car-Mart dealerships. Initial scope: Oklahoma, Missouri, Texas and Kentucky. Greenville, Texas is the qualification pilot.

## Current status

The first hosted Gosom scraper experiment failed qualification: it captured only 1 one-star review against a point-in-time Google listing benchmark of 69. That output is not a comprehensive audit dataset.

Two experimental local collectors now target the rendered Google Maps interface:
- Desktop/laptop Playwright: `tools/local_maps_collector.py`
- Android Firefox userscript: `tools/android_maps_collector.user.js` (v0.5.0)
- Android setup: `ANDROID_PILOT.md`
- Desktop setup: `requirements-local.txt`, `LOCAL_BROWSER_PILOT.md`
- Non-destructive one-star derivation: `tools/filter_one_star.py`
- Android bundle processor: `tools/process_android_bundle.py`

Both collectors are **not yet live-tested**. The Android v0.5.0 build adds a one-click unsorted audit run and automatic single-file evidence-bundle export. It has passed JavaScript syntax parsing but has not yet been exercised against live Google Maps. The desktop path uses Playwright; the Android path uses Firefox plus Violentmonkey and user-controlled visible-card capture. The desktop path verifies Lowest sorting; the Android one-click path deliberately captures the unsorted feed because the Lowest control was unavailable in the tested mobile interface. The Android userscript adds per-listing browser-local persistence and a configurable dealership identity (name, address, phone), so records survive page reloads in the same browser profile and settings can be reused across locations. Version 0.5.0 waits for the exact Greenville profile title plus address and phone checks, then starts without a button tap; it opens Reviews, collects the unsorted visible feed, and automatically downloads one JSON bundle when the feed stalls or collection is stopped. A manual RUN AUDIT button remains available. This deliberately avoids dependence on the missing Lowest control; the manifest records that the sort is unverified. It exports raw and one-star JSONL/CSV plus a manifest. The desktop filter derives one-star records without modifying raw captures. The Android bundle processor independently re-derives one-star rows from the one-click JSON bundle and writes raw JSONL, one-star JSONL/CSV, hashes, and a reconciliation manifest. Neither path declares completeness automatically. The next engineering gate is a live Greenville run that proves correct listing identity, real feed movement, accurate field extraction, and count reconciliation; Lowest sorting is not a prerequisite for the Android all-ratings path.

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

See [LOCAL_BROWSER_PILOT.md](LOCAL_BROWSER_PILOT.md) for the desktop setup and [ANDROID_PILOT.md](ANDROID_PILOT.md) for the phone-based Firefox/Violentmonkey candidate. Neither has yet passed a live Google Maps test.

## Outputs

The desktop pilot writes raw JSONL and a scroll/identity manifest; `tools/filter_one_star.py` derives one-star JSONL and CSV without altering the raw file. The Android pilot exports raw JSONL, one-star JSONL, one-star CSV, and a manifest from the browser session.

Do not submit these outputs as a comprehensive audit until the Greenville qualification gates pass. Expand to other dealerships only after the pilot is repeatable and independently verified.
