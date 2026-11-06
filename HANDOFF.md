# Review Audit Tool — engineering handoff

Last maintained: 2026-11-06
Repository: https://github.com/danielrichert74-oss/crmt-review-audit
Hard rule: $0 only. No paid APIs, credits, subscriptions, proxies, paid browser agents, hosted compute, GitHub Actions, or uncertain billing.

## Product identity
Public name: **Review Audit Tool**.
Initial deployment target: Android Firefox + Violentmonkey, public Google Maps reviews.
Qualification pilot: Car-Mart of Greenville, Texas.
This tool collects and analyzes public review evidence; review allegations are not independently verified facts and do not alone prove corporate liability.

## Current components
- Android collector: `tools/android_maps_collector.user.js`, v0.7.1.
- Processor: `tools/process_android_bundle.py`.
- Existing filter: `tools/filter_one_star.py`.
- Android guide: `ANDROID_PILOT.md`.
- Overview: `README.md`.
- Engineering history: `STATUS.md`.
- Processor tests: `tests/test_process_android_bundle.py`.
- Desktop prototype: `tools/local_maps_collector.py` (not qualified).

## Current implementation
- Android collector has a fail-closed Greenville identity check (name, address, phone), opens Reviews, captures the unsorted visible feed, attempts automatic traversal, and exports a JSON bundle.
- Feed detection prefers scrollable `[role=feed]`, otherwise ranks scrollable review-containing regions.
- Bundle includes a bounded trace (max 600 cycles): timestamps, unique/new-card counts, visible card counts, scrollTop, scrollHeight, clientHeight, and bottom observation.
- Processor summarizes trace cycles, new-card totals, cycles with new cards, max scrollTop/height, and bottom observations.
- Lowest machine verification requires an explicit selected-state signal. Default one-click path does not rely on Lowest; it derives one-star records after raw capture.
- Raw reviews are retained separately from derived one-star records.
- Bundle and processor manifest always preserve `complete: false`.

## Latest commits
- `bfb5a8236b588e76955ef67830e499a1f788679d` — v0.7.0 branding/version.
- `15c04f9114029177b3860259ebad953e467748f2` — README product naming.
- `f3ca4b6343488b37af1eca05f2b6b09853bd4b08` — Android guide.
- `d468d7ad16dddf24fb8b6d815a9391de6d1751f0` — scroll-trace capture.
- `6800dcd1e438b753a47748739c83406039238b4e` — processor trace summary.
- `bb87daee84e6e89ecc65d266d5b28ca12708f789` — trace-summary fixture test.
- `adad5eee91644b910caecc6fec3cb4789e1ff4df` — scroll-trace status update.
- `ce6a439cf88561dc308066e3e0af26e1151ba01f` — persistent engineering handoff created.
- `fd26678f01c5d5123279d8b0699e6d37c04b49fc` — product naming/handoff status entry.
- `4d06c4dee822c287e681d94fccad062377ea8bb6` — persistent revision notes created.

## QA branch changes — 2026-11-06
- Branch: `qa-hardening-2026-11-06`.
- Fixed a blocking JavaScript syntax defect: `runUnsortedAudit` contained `await` but was not declared `async`. Both automatic and manual startup paths now catch startup rejections and fail safely.
- Runtime banner and evidence collector identifier now consistently report v0.7.1.
- Processor rejects boolean star ratings, reports a five-star/unknown distribution, and flags declared-vs-valid trace-count mismatches and supplied-subset disagreement.
- Added source regression checks for async declaration, version alignment, and both guarded startup paths, plus processor fixtures for boolean ratings and trace integrity.

## Verification — precise status
- A source review found and fixed a blocking async syntax defect that earlier static checks had missed. Do not rely on the older syntax-pass statement as validation of v0.7.0.
- Nine targeted static checks passed for trace fields, export, bounded length, and incomplete flag.
- Prior broader v0.6.0 static acceptance set passed 15/15 before trace addition.
- New QA branch tests have not yet been executed in a full checkout. No test-run result is claimed.
- **No live Google Maps DOM test or live Firefox Android collection has passed.** Selectors, identity gate, feed choice, traversal, extraction, download, and persistence need live qualification.
- Never claim deployment-ready, complete historical coverage, or systemic findings until a real run, repeatability, reconciliation, and source spot-check gates pass.

## Resume plan — do not repeat completed work
1. Run the full Python unittest suite in a local checkout, including `tests/test_android_userscript_source.py` and `tests/test_process_android_bundle.py`; use a local Python installation only (no hosted workflows).
2. Do not recreate retired hosted Gosom/Stophy experiments or workflows; they failed qualification and violated the $0 guardrail.
3. Review v0.7.0 for deterministic defects: identity continuity, auto-start, feed selection, scroll trace, extraction, localStorage, duplicate-key collisions, bundle export.
4. Add useful offline tests only; do not create fake-DOM tests that could be mistaken for a live Google Maps qualification.
5. Improve provenance in processor: original bundle hash, listing identity, collector version, capture times, trace summary, unknown/missing-field counts, explicit limitations.
6. After Greenville is live-qualified, define multi-dealership configuration and manifest. Each dealership needs independently verified name, address, phone, and canonical profile URL. Never reuse Greenville identity for another branch.
7. Define a cross-location schema: source URL, capture timestamp, rating, text, reviewer/date, location identity, raw card text, source bundle hash, collector version. Keep raw and derived data separate.
8. Quality report must include benchmark source/time, observed vs captured counts, scroll trace movement, duplicates, missing fields, rating distribution, spot-check results, and reasons coverage is incomplete.
9. Deployment gate: real Android run must show verified listing identity, reviews loading, scroll position advancing, new cards captured, correct ratings/text/date extraction, automatic bundle download, successful processor run, and repeat-run consistency.
10. Maintain $0. Never ask the user to manually copy review text. The only user-side action that may be unavoidable is opening the installed collector on the target phone for live qualification. The assistant cannot remotely operate that device or continue executing after a chat session ends.

## Resume instruction
At the start of a new session, read this file first, then fetch the current userscript, processor, tests, README, and STATUS. Continue at Resume plan. Do not ask the user to restate the project or repeat retired experiments. Do not claim live qualification without fresh evidence.


## Evidence preservation and Android download fallback
- v0.7.1 now retains separate DOM-node observations when Google Maps omits a stable review ID. Each such observation carries a content fingerprint for later reconciliation.
- The processor preserves all observed one-star rows. Matching Google review IDs/content fingerprints are reported as potential duplicates; they are not silently removed because matching content can represent distinct genuine reviews.
- A dedicated **Export full evidence bundle** panel action is available as a direct user-gesture download fallback.
- New tests cover repeated review IDs and distinct review IDs with identical text. Execute the complete suite in a local checkout before promoting the candidate.
