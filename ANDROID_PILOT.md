# Review Audit Tool — Android Firefox collector

## Why this path

The Playwright collector requires a desktop/laptop. This experimental alternative
runs as a userscript inside Firefox for Android, so the phone can operate the
visible Google Maps page. It is based on ordinary page DOM access and local
browser downloads; it has no API key, paid service, proxy, external upload, or
background server.

Files:
- `tools/android_maps_collector.user.js` — Review Audit Tool userscript
- `tools/filter_one_star.py` — JSONL one-star derivation
- `tools/process_android_bundle.py` — processor for the one-click JSON bundle

## One-time browser setup

1. Install Firefox for Android if it is not already installed.
2. In Firefox, open the Add-ons menu and find **Violentmonkey**. Confirm that
   the listing says it is available for Firefox for Android.
3. Install it and grant the extension's requested website access. Violentmonkey
   needs permission to run on Google Maps pages.
4. Open the repository file
   `tools/android_maps_collector.user.js` while signed into GitHub. Use the
   Raw view, then install the userscript in Violentmonkey. If Android does not
   offer direct installation from the Raw view, create a new script in
   Violentmonkey and paste the file contents.

## Greenville pilot

1. Open the Google Maps business overview for CAR-MART of Greenville, Texas.
2. The userscript waits for the exact profile title, address, and phone checks, then starts automatically. If it does not start, tap **RUN AUDIT (all reviews)**.
3. Keep Firefox on the listing while the collector opens Reviews, captures visible cards, and scrolls the feed.
4. When collection stops, preserve the automatically downloaded JSON evidence bundle unchanged.

The one-click route deliberately captures the default/unsorted review feed. It does not depend on a Lowest sort control, which was missing in the mobile interface. The processor derives one-star records from the captured raw cards afterward.
The default identity gate is CAR-MART of Greenville, 5107 Interstate Highway
30, Greenville, TX 75402, phone 903-458-9900. Do not use this build for another
location without changing and reviewing those expected values.

### Automatic unsorted run (v0.7.0)

Open the Greenville dealership overview page in Firefox. Once the script detects
the exact profile title plus matching address and phone, it starts automatically:
it opens the Reviews tab, waits for review cards, then scrolls and captures the
rendered feed. If automatic start does not trigger, tap **RUN AUDIT (all reviews)**. The route
does not require the Lowest sort control, which was missing in the prior mobile
UI attempt. The one-star set is derived from all captured ratings after collection.

When the feed appears exhausted (or collection is manually stopped), the script
automatically downloads one JSON evidence bundle containing raw reviews, the
derived one-star subset, identity checks, feed-detection diagnostics, per-cycle scroll trace, collection timestamps, scroll count,
stop reason, field-missing counts, and an explicit `complete: false` flag.
Keep the tab open during collection. The one-click run is still experimental:
version 0.7.0 prefers the explicit scrollable review feed and records how the feed was selected; feed exhaustion is not proof that Google exposed every historical review, and
the captured count must be reconciled against a fresh source benchmark.

## Important limitations

- Version 0.7.0 improves feed selection and records per-cycle traversal by preferring a scrollable `[role=feed]`, then ranking scrollable review-containing containers; the bundle records the selection method and dimensions. This remains a prototype and has not been tested on a live Google Maps page or
  on the user's Android device.
- The page's mobile DOM may differ from desktop, and Google may change selectors.
- Identity verification must be performed on the business overview before
  opening Reviews because the review view may hide address/contact metadata.
- The script only captures review cards that become visible in the page. It
  disarms if the verified business name is no longer visible, but it cannot
  establish that all historical reviews were exposed.
- The one-click Android path does not claim a verified sort. It records
  `unverified-or-default-sort` and derives one-star rows after collecting all
  visible ratings. The older manual Lowest buttons remain for diagnostic use.
- Captures are persisted in browser-local storage and the evidence bundle is
  downloaded when auto-collection stops. Keep the tab open during collection;
  do not reload or close it before the bundle is downloaded.
- The manifest and automatic evidence bundle always record `complete: false`.
  Reconcile the captured count against the current Google listing and perform
  independent spot checks before using it as an audit exhibit.
- The userscript does not submit, edit, like, or otherwise interact with reviews.

## Free and privacy characteristics

Firefox and the Violentmonkey add-on are free to install. The script itself
uses no paid API or metered browser service. Review data stays in the browser profile's local storage and is exported to
  the device only when the user starts or stops an export-producing collection. The extension
does request permission to access website content so it can run on Google Maps.


### Process the downloaded bundle

After the Android collector downloads `crmt-audit-bundle-*.json`, copy it to a computer and run:

```bash
python tools/process_android_bundle.py --input crmt-audit-bundle.json --outdir output/greenville
```

Optional count comparison (a match is not proof of completeness):

```bash
python tools/process_android_bundle.py --input crmt-audit-bundle.json --outdir output/greenville --benchmark-one-star-count 69
```

The processor recomputes the one-star subset from raw reviews, preserves every raw row, deduplicates the derived one-star set, exports CSV/JSONL, hashes the source and outputs, and writes a manifest. It always records `complete: false`.
