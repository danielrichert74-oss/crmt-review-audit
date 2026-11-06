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


- Added an explicit Android fallback for sort-state variation: **Verify & arm** requires a detected selected-state signal; **Confirm Lowest visually** is a separate user-attested path and is labeled as such in the exported manifest. This avoids silently treating a manual assertion as machine verification.


- Android identity verification now occurs on the business overview before opening Reviews. This matters because current Google Maps extraction guidance reports that the review view may hide address/contact metadata. The verified identity and URL are retained in memory for the session.
- Added a title-continuity guard: if the visible business title changes or disappears after arming, capture disarms rather than risking cross-location contamination.
- Added an explicit manual Lowest-sort confirmation path; the manifest labels it as user-confirmed rather than machine-detected.
- Added unit tests for one-star derivation (deduplication, unknown ratings, malformed JSONL, and review-ID preference). Tests are committed but have not been executed in this environment.


- Android extraction now also preserves the raw visible card text and includes a best-effort date fallback from the card's text when the dedicated date selector is absent. The one-star CSV includes that raw card text for review/quality control.
- The business-continuity check was relaxed from exact heading equality to requiring the verified business name tokens remain visible somewhere in the current page/ARIA text; this accommodates the heading changing in the Reviews view while still disarming if the business identity disappears.


## Offline verification — 2026-11-06

- Executed the committed `filter_one_star.py` source in an isolated temporary directory. Python compilation passed.
- Executed the committed `tests/test_filter_one_star.py` test contents against that source: 2 tests passed.
- End-to-end sample: 5 valid raw records produced 2 unique one-star records; 1 duplicate one-star, 1 non-one-star, 1 unknown rating, and 1 malformed JSONL line were separately accounted for. The derived manifest remained `complete: false`.
- This verifies the derived-filter logic only. It does not test the Playwright collector, the Android userscript in a browser, or live Google Maps extraction.


- Expanded Android manifest counters: non-one-star and unknown-rating counts, plus missing review ID, reviewer, date, and review-text counts. This makes visible-card extraction quality measurable instead of reporting only total and one-star counts.
- Added an additional Google Maps hostname match for the Android userscript.


## Controlled live-test attempt — 2026-11-06

- Re-ran JavaScript syntax validation against the committed Android userscript; parsing passed.
- Checked every declared UI action against the click-handler branches; all 11 actions have handlers.
- Fixed a manifest accuracy issue: `lowest_selected_at_arm` now reflects whether a sort-verification method was actually recorded, rather than being hard-coded true. This was committed separately.
- Live reference check: Car-Mart's official Greenville page confirms 5107 Interstate Highway 30, Greenville, TX 75402 and 903-458-9900, matching the script's expected address and phone. A third-party review aggregator currently reports a Google review subset and 95 one-star reviews; this is not treated as a Google Maps benchmark or as collector output.
- A direct Google Maps page could not be opened through the available web reader. The Android userscript has not been executed in a live browser or on the user's S23.
- Remote browser-agent execution is metered. It was not used because the project's standing $0 constraint prohibits spending credits. No Actions workflow was launched.
- Result: **static QA passed; live collector test remains blocked pending execution in Firefox Android on the target Google Maps listing.** Do not describe the collector as live-tested or qualified.


## Android one-click unsorted collection — 2026-11-06

- Updated the Android userscript to v0.4.0.
- Added a single **RUN AUDIT (all reviews)** action: it verifies the current Greenville overview, attempts to open Reviews, waits for review cards, arms unsorted capture, and starts automatic feed traversal.
- This is a deliberate workaround for the mobile Google Maps UI not exposing a usable Lowest control. The collector preserves all observed ratings and derives one-star rows afterward; the manifest does not claim a verified sort.
- Added automatic single-file JSON bundle export after feed exhaustion or manual stop. The bundle includes raw cards, the derived one-star subset, identity evidence, collection timing, scroll cycles, stop reason, and missing-field counts.
- Added a conservative Reviews-tab label matcher and verified JavaScript syntax parsing in an isolated V8 runtime.
- Repository changes committed; no live Google Maps run was performed. The one-click path is therefore an improved candidate, not yet a qualified audit. The bundle must be reconciled and independently spot-checked before evidentiary use.


## Android bundle processing — 2026-11-06

- Added `tools/process_android_bundle.py` to convert the Android one-click JSON bundle into raw JSONL, independently derived one-star JSONL/CSV, SHA-256 hashes, missing-field counts, optional benchmark comparison, and an audit manifest.
- Added unit tests for duplicate handling, rating recovery from labels, raw preservation, benchmark comparison, and the permanent incomplete flag.
- Fixed escaping in the processor's rating-label regex and JSONL newline writer after inspecting the committed source.
- Two processor tests and two existing one-star-filter tests passed in isolated temporary Python harnesses (4/4). JavaScript collector syntax and static acceptance checks passed. These are code/fixture tests only; live Maps traversal remains untested.


## Automatic launch hardening — 2026-11-06

- Updated Android userscript to v0.5.0.
- It now waits up to 45 seconds for the selected page title itself to identify CAR-MART of Greenville and for the configured address and phone checks to pass. Only then does it open Reviews and begin the unsorted all-ratings capture automatically.
- The manual RUN AUDIT button remains as a fallback. Tightened the title gate to avoid auto-starting merely because a search-results page contains the dealership name in unrelated page text.
- JavaScript syntax parsing passed after the change. This remains a candidate build pending live Android/Google Maps qualification.

- Tightened the automatic identity gate so a single h1 or document-title source must contain both CAR-MART and Greenville; the collector records the matching title rather than a generic page heading. JavaScript syntax parsing passed.
- Added a fallback scan of scrollable containers containing review cards when the card-ancestor and role=feed selectors fail. The userscript's embedded collector version label is aligned to v0.5.0; JavaScript syntax parsing passed.
- Added a partial-bundle fallback: if review cards are captured but no scroll container can be identified, the collector now exports the partial evidence bundle instead of leaving records only in browser storage. JavaScript syntax parsing passed.

## Strict $0 safeguard — 2026-11-06

- Deleted both legacy GitHub Actions collection workflows: the Stophy API workflow and the hosted Gosom/Docker workflow.
- This prevents accidental invocation of a metered third-party API or consumption of hosted compute minutes. The active Android and desktop collectors remain local visible-browser candidates.


## Android feed-discovery hardening — 2026-11-06

- Updated the Android collector to v0.6.0.
- Feed selection now prefers a scrollable element explicitly marked `role=feed`; otherwise it evaluates scrollable review-containing containers and ranks them by descendant review-card count, scroll range, and area.
- The exported evidence bundle records the selected feed-detection method, candidate count, role, class name, and initial scroll dimensions. This makes a failed or suspicious traversal diagnosable from the evidence file rather than relying on screenshots or manual review copying.
- JavaScript syntax parsing and static acceptance checks passed after the change.
- No live Google Maps or Android-device test has been performed. The change improves the candidate's logic but does not establish that the current Maps mobile DOM will expose a usable feed.


## Lowest-sort false-positive correction — 2026-11-06

- Tightened machine verification for the legacy Lowest-sort mode. A button label that merely contains the word "Lowest" is no longer accepted as proof that Lowest is selected; the collector now requires an explicit selected-state signal on the Lowest option.
- This prevents a menu action label from being mistaken for an applied sort state. The separate user-visually-confirmed mode remains available and is explicitly labeled in the evidence.
- JavaScript syntax parsing passed. Static acceptance checks passed for all three collection paths (automatic unsorted, explicit unsorted, machine-detected Lowest, and user-confirmed Lowest), feed traversal/safety stops, automatic/partial bundle export, raw preservation, one-star derivation, identity gate, and incomplete-coverage flag (15/15 checks).
- These are code/static checks, not live Google Maps DOM tests. No live-device qualification is claimed.


## Scroll-trace evidence hardening — 2026-11-06

- Android collector now records a bounded per-cycle traversal trace in the exported bundle: cycle number, timestamp, unique capture count, newly captured count, visible card count before/after scroll, scrollTop before/after, scrollHeight before/after, client height, and whether the feed reached its bottom.
- The trace is capped at 600 cycles to keep the bundle bounded. It is diagnostic evidence of what the browser session did, not proof that Google exposed every historical review.
- Re-fetched the committed userscript after the change; JavaScript syntax parsing passed and all 9 targeted static checks passed, including trace export and the permanent `complete: false` safeguard.
- This is static verification only. It does not establish that the selected container is the real review feed or that cards load correctly on the user's live Android Google Maps page.


- Extended the offline bundle processor to summarize the Android scroll trace in the audit manifest: valid trace cycles, reported new-card counts, cycles with new cards, maximum observed scroll position/height, and bottom-state observations.
- Added a fixture test for this summary and confirmed the permanent incomplete flag remains false in the test assertion. The test has been committed but has not yet been executed in a real Python checkout in this environment.


## Product naming and handoff — 2026-11-06

- Adopted **Review Audit Tool** as the product name.
- Android userscript metadata, visible panel title, and evidence collector identifier now use Review Audit Tool v0.7.0.
- README and Android deployment guide updated for the product name and v0.7.0 scroll-trace capability.
- Added `HANDOFF.md` with current architecture, exact latest commits, verification boundaries, $0 constraints, deployment gates, and a resume checklist to prevent repeated experiments after a session interruption.
- No live browser/device qualification is claimed. The product remains in pilot engineering until real Android capture and reconciliation pass.


## QA hardening branch — 2026-11-06

- Created branch `qa-hardening-2026-11-06` for a focused processor/collector maintenance pass.
- Processor now rejects boolean values as star ratings (Python treats `True` as integer 1), emits a 1–5 plus unknown rating distribution, and flags mismatches between the declared trace cycle count and valid trace records. It also flags disagreement between the collector-supplied one-star subset and independent raw-card derivation.
- Added regression tests for boolean-rating rejection and trace-count mismatch warnings.
- Aligned the userscript runtime startup label and evidence collector version to 0.7.1; removed the stale 0.6.0 startup message.
- These changes are committed on the QA branch. They have not yet been executed in a Python test environment or live Firefox/Google Maps. Do not merge or label deployment-ready until test execution and the live Android deployment gates in HANDOFF.md pass.


- Follow-up source review found a blocking defect missed by earlier static checks: `runUnsortedAudit` contained an `await` expression but was not declared `async`. Corrected the declaration and added rejection handling to both auto-launch and button-launch paths. Added a source regression test to prevent recurrence. This demonstrates why the previous syntax-pass notes should not be treated as proof of live behavior; the 0.7.1 branch still needs local test execution and live device qualification.


- Evidence-preservation hardening: the collector now keys no-ID cards by stable DOM-node/content-signature observations, preserves same-content cards from separate DOM nodes, and records a potential-duplicate fingerprint. The processor no longer discards matching one-star rows; it preserves every observed row and reports potential duplicate counts/fingerprints. This avoids deleting a legitimate distinct review merely because its content matches another review.
- Added a direct **Export full evidence bundle** button as a user-gesture fallback if an automatic mobile download is blocked.
- Expanded regression fixtures to cover repeated Google review IDs and separate review IDs with identical content. Full repository test execution and live Android qualification remain outstanding.

- Candidate version advanced to 0.7.2 after duplicate-preservation and mobile full-bundle export changes; source regression tests now expect 0.7.2. Targeted logic checks passed; no full-checkout test or live Android result is claimed.
