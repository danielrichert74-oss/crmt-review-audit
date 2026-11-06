# Android Firefox pilot — CRMT review capture

## Why this path

The Playwright collector requires a desktop/laptop. This experimental alternative
runs as a userscript inside Firefox for Android, so the phone can operate the
visible Google Maps page. It is based on ordinary page DOM access and local
browser downloads; it has no API key, paid service, proxy, external upload, or
background server.

Files:
- `tools/android_maps_collector.user.js` — userscript
- `tools/filter_one_star.py` — optional desktop-side JSONL processor for a
  downloaded raw file

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

1. In Firefox, open Google Maps and search for CAR-MART of Greenville, Texas.
2. Open the business profile overview. Before opening Reviews, tap **Verify
   business**. Google may hide address and phone details after switching to
   the review view, so identity is checked on the overview page first.
3. Open Reviews and choose the **Lowest** review sort in Google Maps.
4. Tap **Arm (Lowest detected)** if the script detects Google's selected state.
   If the live UI does not expose that state, visually confirm Lowest is
   selected and tap **Arm (Lowest confirmed visually)** instead. The manifest
   distinguishes automatic DOM verification from user confirmation.
5. Tap **Capture visible**, then **Scroll feed once**. Allow the page to load,
   and capture again. Repeat while the list continues to load. The script also
   watches page changes and deduplicates cards it sees.
6. Export **raw JSONL**, **one-star JSONL**, **one-star CSV**, and **manifest**.
   Keep the raw file and manifest together as source artifacts.

The default identity gate is CAR-MART of Greenville, 5107 Interstate Highway
30, Greenville, TX 75402, phone 903-458-9900. Do not use this build for another
location without changing and reviewing those expected values.

### One-click unsorted run (v0.4.0)

From the dealership overview page, tap **RUN AUDIT (all reviews)**. The script
checks the dealership name/address/phone, opens the Reviews tab, waits for review
cards, then scrolls and captures the rendered feed automatically. It does not
require the Lowest sort control, which was missing in the prior mobile UI
attempt. The one-star set is derived from all captured ratings after collection.

When the feed appears exhausted (or collection is manually stopped), the script
automatically downloads one JSON evidence bundle containing raw reviews, the
derived one-star subset, identity checks, collection timestamps, scroll count,
stop reason, field-missing counts, and an explicit `complete: false` flag.
Keep the tab open during collection. The one-click run is still experimental:
feed exhaustion is not proof that Google exposed every historical review, and
the captured count must be reconciled against a fresh source benchmark.

## Important limitations

- This is a prototype. It has not been tested on a live Google Maps page or
  on the user's Android device.
- The page's mobile DOM may differ from desktop, and Google may change selectors.
- Identity verification must be performed on the business overview before
  opening Reviews because the review view may hide address/contact metadata.
- The script only captures review cards that become visible in the page. It
  disarms if the verified business name is no longer visible, but it cannot
  establish that all historical reviews were exposed.
- The sort-state detector may not recognize every Google Maps UI version.
  The separate manual confirmation button records that the user visually
  selected Lowest; it is not represented as automatic DOM verification.
- The capture is held in the current page session until exported. Do not reload
  or close the tab before exporting.
- The manifest and automatic evidence bundle always record `complete: false`. Reconcile the captured count
  against the current Google listing and perform independent spot checks before
  using it as an audit exhibit.
- The userscript does not submit, edit, like, or otherwise interact with reviews.

## Free and privacy characteristics

Firefox and the Violentmonkey add-on are free to install. The script itself
uses no paid API or metered browser service. Review data stays in the page's
in-memory session until the user explicitly downloads an export. The extension
does request permission to access website content so it can run on Google Maps.
