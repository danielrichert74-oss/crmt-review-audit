# Review Audit Tool — revision notes

## 2026-11-06 — v0.7.0
- Standardized product name as Review Audit Tool.
- Branded Android userscript metadata and visible panel.
- Updated evidence collector identifier to `review-audit-tool-android-0.7.0`.
- Added bounded per-cycle scroll trace to the Android bundle.
- Added processor trace summary to the audit manifest.
- Static syntax and targeted checks passed; no live Maps/Android qualification has passed.
- $0 restriction retained; retired hosted collection workflows remain deleted.

## Resume without repeating
Read `HANDOFF.md` first. It contains current state, commit references, constraints, qualification gates, and the next engineering sequence. Fetch current source from the default branch before modifying anything. Do not rely on older chat summaries where repository state is newer.


## 2026-11-06 — QA hardening branch
- Bumped Android collector to 0.7.1 and corrected its stale 0.6.0 startup message.
- Processor rejects boolean ratings, reports rating distribution, and flags trace-count and supplied-subset integrity mismatches.
- Added regression fixtures for boolean rating rejection and trace integrity warnings.
- Branch: `qa-hardening-2026-11-06`.
- No claim of test execution or live browser qualification. Run the documented tests and real Android acceptance gate before deployment.
