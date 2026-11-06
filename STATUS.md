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
