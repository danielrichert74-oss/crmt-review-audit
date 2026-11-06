#!/usr/bin/env python3
"""Prepare a direct Google Maps URL and retain only one-star reviews from gosom output."""
import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEALERSHIPS = ROOT / "data" / "dealerships.csv"


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load_pilot():
    with DEALERSHIPS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    rows = [r for r in rows if r.get("city", "").strip().lower() == "greenville"
            and r.get("state", "").strip().upper() == "TX"]
    if len(rows) != 1:
        raise RuntimeError(f"Expected exactly one Greenville, TX dealership row; found {len(rows)}")
    row = rows[0]
    if not row.get("official_google_maps_link", "").startswith("https://www.google.com/maps/"):
        raise RuntimeError("Greenville row does not contain an official Google Maps URL")
    return row


def parse_records(path):
    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        raise RuntimeError("Scraper output is empty")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            # Some writers wrap the output in a results array.
            for key in ("results", "data", "items"):
                if isinstance(parsed.get(key), list):
                    return parsed[key]
            return [parsed]
    except json.JSONDecodeError:
        pass
    records = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid JSON on output line {number}: {exc}") from exc
        if isinstance(item, list):
            records.extend(item)
        else:
            records.append(item)
    return records


def iso_from_micros(value):
    try:
        return dt.datetime.fromtimestamp(int(value) / 1_000_000, tz=dt.timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-input", type=pathlib.Path)
    parser.add_argument("--raw", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "output")
    args = parser.parse_args()

    pilot = load_pilot()
    if args.prepare_input:
        args.prepare_input.parent.mkdir(parents=True, exist_ok=True)
        args.prepare_input.write_text(pilot["official_google_maps_link"].strip() + "\n", encoding="utf-8")
        print("Prepared one exact Google Maps listing URL for Greenville, TX.")
        return 0

    if not args.raw:
        parser.error("--raw is required unless --prepare-input is used")

    records = parse_records(args.raw)
    expected_phone = norm(pilot.get("phone"))
    expected_address = norm(pilot.get("address"))
    expected_city = norm(pilot.get("city"))
    expected_name = norm(pilot.get("store_name"))
    matches = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        phone_ok = expected_phone and norm(entry.get("phone")) == expected_phone
        address = norm(entry.get("address"))
        title = norm(entry.get("title"))
        name_ok = ("carmart" in title or "car-mart" in str(entry.get("title", "")).lower())
        address_ok = ("greenville" in address and "5107" in address)
        if phone_ok or (name_ok and address_ok):
            matches.append(entry)

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one verified Greenville listing, found {len(matches)}; "
            "no review records will be written."
        )

    place = matches[0]
    listing_url = place.get("link") or pilot["official_google_maps_link"]
    review_objects = []
    for field in ("user_reviews", "user_reviews_extended"):
        value = place.get(field)
        if isinstance(value, list):
            review_objects.extend(x for x in value if isinstance(x, dict))

    seen = set()
    one_star = []
    duplicates = 0
    for review in review_objects:
        rating = review.get("rating_float")
        if rating is None:
            rating = review.get("Rating", review.get("rating"))
        try:
            is_one_star = float(rating) == 1.0
        except (TypeError, ValueError):
            is_one_star = False
        if not is_one_star:
            continue

        review_id = review.get("review_id") or ""
        text_value = (review.get("text_original") or review.get("text_translated")
                      or review.get("Description") or review.get("description") or "")
        author = review.get("Name") or review.get("name") or ""
        posted = review.get("published_at") or iso_from_micros(
            review.get("posted_at_unix_micros")
        ) or review.get("When") or review.get("when") or ""
        dedupe_key = review_id or (author, posted, text_value)
        if dedupe_key in seen:
            duplicates += 1
            continue
        seen.add(dedupe_key)
        one_star.append({
            "dealership": pilot.get("store_name"),
            "city": pilot.get("city"),
            "state": pilot.get("state"),
            "dealership_address": pilot.get("address"),
            "dealership_phone": pilot.get("phone"),
            "listing_url": listing_url,
            "review_id": review_id,
            "rating": 1,
            "review_text": text_value,
            "reviewer_name": author,
            "reviewer_profile_url": review.get("author_url") or "",
            "published_at": posted,
            "review_url": "",
            "owner_reply_text": review.get("reply_text_original") or review.get("reply_text") or "",
            "owner_reply_at": iso_from_micros(review.get("reply_posted_at_unix_micros")) or "",
            "language": review.get("language") or "",
            "collected_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_collector": "gosom/google-maps-scraper",
        })

    rating_counts = place.get("reviews_per_rating") or {}
    expected_one_star = rating_counts.get("1", rating_counts.get(1))
    try:
        expected_one_star = int(expected_one_star) if expected_one_star is not None else None
    except (TypeError, ValueError):
        expected_one_star = None

    complete = expected_one_star is not None and len(one_star) == expected_one_star
    limitations = [
        "The upstream scraper documents extended review extraction of up to approximately 300 reviews per place.",
        "One-star filtering is applied locally after extraction; non-one-star reviews are discarded and not included in audit outputs.",
        "The upstream review structure does not expose an individual review permalink; review_id and reviewer profile URL are retained instead.",
        "Google may limit, omit, or change review data; compare captured count against Google's per-rating listing count.",
        "Review statements are user-generated allegations and have not been independently verified.",
    ]
    if expected_one_star is None:
        limitations.append("Google's per-rating count was unavailable; completeness cannot be established.")
    elif not complete:
        limitations.append(
            f"Google listing reports {expected_one_star} one-star reviews; collector retained {len(one_star)}. "
            "Coverage is incomplete or the source count changed during collection."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl = args.output_dir / "reviews.jsonl"
    with jsonl.open("w", encoding="utf-8") as handle:
        for item in one_star:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    import csv as csv_module
    csv_path = args.output_dir / "reviews.csv"
    fields = list(one_star[0].keys()) if one_star else [
        "dealership", "city", "state", "dealership_address", "dealership_phone",
        "listing_url", "review_id", "rating", "review_text", "reviewer_name",
        "reviewer_profile_url", "published_at", "review_url", "owner_reply_text",
        "owner_reply_at", "language", "collected_at_utc", "source_collector",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv_module.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(one_star)

    manifest = {
        "project": "America's Car-Mart review audit",
        "pilot": "Greenville, TX",
        "collector": "gosom/google-maps-scraper",
        "source_listing": listing_url,
        "verified_business": {
            "name": place.get("title"),
            "address": place.get("address"),
            "phone": place.get("phone"),
            "place_id": place.get("place_id"),
        },
        "source_review_count": place.get("review_count"),
        "source_reviews_per_rating": rating_counts,
        "reviews_extracted_before_filter": len(review_objects),
        "one_star_reviews_captured": len(one_star),
        "duplicate_one_star_reviews_removed": duplicates,
        "expected_one_star_reviews_from_listing": expected_one_star,
        "one_star_coverage_complete_by_count": complete,
        "complete": complete,
        "limitations": limitations,
        "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if complete else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"COLLECTION FAILED SAFELY: {exc}", file=sys.stderr)
        raise SystemExit(1)
