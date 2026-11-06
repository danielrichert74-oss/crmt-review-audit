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
- Android collector: `tools/android_maps_collector.user.js`, v0.7.0.
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
- `adad5eee91644b910caecc6fec3cb4789e1ff4df` — status update.

## Verification — precise status
- Latest userscript passed JavaScript syntax parsing after trace changes.
- Nine targeted static checks passed for trace fields, export, bounded length, and incomplete flag.
- Prior broader v0.6.0 static acceptance set passed 15/15 before trace addition.
- Earlier processor fixture tests passed in an isolated reconstructed harness; the newly added trace-summary test has not yet been executed in a full checkout.
- **No live Google Maps DOM test or live Firefox Android collection has passed.** Selectors, identity gate, feed choice, traversal, extraction, download, and persistence need live qualification.
- Never claim deployment-ready, complete historical coverage, or systemic findings until a real run, repeatability, reconciliation, and source spot-check gates pass.

## Resume plan — do not repeat completed work
1. Fetch current repository HEAD and relevant files before editing.
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
