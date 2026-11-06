# Engineering status — 2026-11-06

## Current conclusion

The hosted Gosom experiment is a failed qualification test, not a completed collection:
- The scraper built and ran.
- Its live Google Maps collection stopped after five total review cards.
- Only one captured card was one-star.
- The listing benchmark observed during that run was 69 one-star reviews.
- Therefore the run captured 1 of 69 benchmark one-star reviews (about 1.4%); it is not suitable as an audit dataset.

The benchmark is a point-in-time comparison, not proof that Google exposes all historical reviews through any one interface.

## New experiment committed

An experimental local visible-browser collector was added:
- tools/local_maps_collector.py
- requirements-local.txt
- LOCAL_BROWSER_PILOT.md

It uses Playwright and the rendered public Google Maps interface. It does not depend on the Gosom RPC review path. It attempts to open the listing, open Reviews, choose Lowest, discover the scrollable review feed, and preserve each newly seen review card while scrolling.

## Qualification status

**Not yet live-tested.** The new collector is a prototype, not a proven solution. It never sets complete=true. It records the stop reason and scroll trace because a stalled list is not proof of end-of-list.

Before the output can be used:
1. Confirm the correct Greenville business profile is open.
2. Confirm Reviews panel and Lowest sort were actually selected.
3. Confirm scroll position and/or newly loaded card count changes as expected.
4. Inspect captured records for correct rating, text, reviewer, date and owner reply.
5. Compare one-star count against a fresh listing benchmark and independently spot-check the source.
6. Repeat the collection and explain any differences.

## Architecture decision

Keep raw capture separate from derived evidence:
- raw UI captures are retained as source artifacts;
- normalized one-star records are a derived dataset;
- manifests retain listing identity, collection times, collector version, scroll trace, counts, duplicates, and limitations;
- completeness is an explicit verification outcome, never inferred from a successful process exit.

## Zero-cost rule

No paid APIs, paid credits, subscriptions, proxies, card trials, or billing-enabling upgrades are authorized. If a proposed path has uncertain charges, do not use it.

## Maintenance pass — 2026-11-06

- Corrected the README so it no longer describes the failed Gosom experiment as the active collection design.
- Fixed a JSONL serialization defect in the local collector: each captured review is now terminated by an actual newline, rather than the two-character literal sequence `\\n`.
- Re-fetched the committed source and verified the corrected write statement is present.
- These are repository/code inspections only. They do not constitute a Python runtime test or a live Google Maps test.


- Added a fail-closed identity gate to the visible-browser collector: it will not open Reviews or collect cards unless the selected Google Maps profile title contains both CAR-MART and Greenville. The manifest records `identity_verified_by_title`.
- This is a minimum title-based gate, not complete address/phone verification. It prevents an obvious wrong-profile scrape but does not replace manual identity review.
- No live Google Maps run or Python runtime test was performed in this maintenance pass.


- Tightened sort qualification: the collector now selects Lowest, reopens the sort menu, and requires an explicit selected-state signal (`aria-checked`, `aria-selected`, or `data-selected`) before it will collect. The evidence or failure reason is recorded in the manifest. This is intentionally fail-closed and may need adjustment if Google's live DOM exposes a different signal.
- Corrected the exact-text Lowest selector after reviewing the committed source.
- Still no runtime or live-browser test: no Actions run was launched because the repository's remaining free compute allowance is unknown, and the $0 rule prohibits risking billable usage. TinyFish browser automation is also metered, so it was not used.


## Collector hardening pass — 2026-11-06

- Added a stricter Greenville identity gate: the selected profile title must contain CAR-MART and Greenville, the visible page text must contain every token from the expected street address, and the expected phone digits must appear. The manifest records each check separately. This is still a UI-text match, not independent proof of the underlying listing identity; inspect the opened profile during the pilot.
- Added a best-effort click on card-local "More" controls before extracting review text, and a best-effort owner-response date field. Google UI selectors may change and these fields require live validation.
- Added `tools/filter_one_star.py`, a non-destructive derivation step that preserves the raw mixed-rating JSONL, deduplicates one-star rows, exports JSONL and CSV, and separately counts unknown ratings, invalid ratings, duplicates, and malformed lines.
- Corrected the expected-phone digit-normalization regex after inspecting the committed source.
- Updated the pilot instructions with identity flags and one-star derivation command.
- These changes have been committed, but no Python execution, browser execution, or live Google Maps collection has yet been performed. They are code-level hardening only.


## Android route added — 2026-11-06

A second local collection interface has been added for the phone:
- `tools/android_maps_collector.user.js` is a Violentmonkey userscript for Firefox Android.
- `ANDROID_PILOT.md` documents installation and a manual Greenville test.
- The panel requires the Greenville title/address/phone checks and a recognized Lowest-sort state before arming. It captures visible cards, deduplicates them in the current tab session, and exports raw JSONL, one-star JSONL, one-star CSV, and a manifest.
- The manifest always says `complete: false`. The script does not upload data or call a paid service.
- The script was code-reviewed and corrected for regular-expression escaping, mutation-observer recursion, and export-manifest wiring. It has **not** been run on a live Google Maps page or tested on the user's Android device.

Mozilla's current Android add-on help documents installing compatible extensions through Firefox's Add-ons manager, and the Violentmonkey listing identifies Firefox for Android support. This makes the path technically plausible, not yet qualified for audit collection.
