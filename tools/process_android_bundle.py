#!/usr/bin/env python3
"""Process a CRMT Android v0.4+ JSON evidence bundle into auditable files.

The input bundle is preserved. Raw cards are exported without filtering;
one-star records are independently re-derived from raw_reviews. The output
manifest never marks coverage complete automatically.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIELDS = [
    "review_id", "capture_key", "reviewer_name", "reviewer_profile_url",
    "rating_label", "rating_value", "published_at", "review_text",
    "owner_reply_text", "owner_reply_date", "listing_title", "listing_url",
    "collected_at_utc", "collector", "card_text",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_key(row: dict[str, Any]) -> str:
    source_id = row.get("review_id") or row.get("capture_key")
    if source_id:
        return str(source_id)
    material = "|".join(str(row.get(key) or "") for key in (
        "reviewer_name", "published_at", "review_text", "rating_label"
    ))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def rating_value(row: dict[str, Any]) -> int | None:
    value = row.get("rating_value")
    if value is None:
        label = str(row.get("rating_label") or "")
        import re
        match = re.search(r"([1-5](?:\.0+)?)\s*star", label, re.I)
        value = match.group(1) if match else None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric not in (1.0, 2.0, 3.0, 4.0, 5.0):
        return None
    return int(numeric)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Android audit bundle JSON")
    parser.add_argument("--outdir", default="output/android-audit")
    parser.add_argument("--benchmark-one-star-count", type=int, default=None)
    args = parser.parse_args()

    source = Path(args.input)
    output = Path(args.outdir)
    output.mkdir(parents=True, exist_ok=True)
    bundle = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict) or not str(bundle.get("schema_version", "")).startswith("crmt-review-audit-bundle-"):
        raise SystemExit("Input is not a recognized CRMT Android audit bundle.")

    raw = bundle.get("raw_reviews")
    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
        raise SystemExit("Bundle raw_reviews must be an array of review objects.")

    listing = bundle.get("listing") if isinstance(bundle.get("listing"), dict) else {}
    collection = bundle.get("collection") if isinstance(bundle.get("collection"), dict) else {}
    normalized: list[dict[str, Any]] = []
    for source_row in raw:
        row = dict(source_row)
        row["rating_value"] = rating_value(row)
        normalized.append(row)

    one_star_all = [row for row in normalized if row["rating_value"] == 1]
    seen: set[str] = set()
    one_star: list[dict[str, Any]] = []
    duplicates = 0
    for row in one_star_all:
        key = record_key(row)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        one_star.append(row)

    raw_path = output / "raw_reviews.jsonl"
    one_path = output / "one_star_reviews.jsonl"
    csv_path = output / "one_star_reviews.csv"
    manifest_path = output / "audit_manifest.json"
    write_jsonl(raw_path, normalized)
    write_jsonl(one_path, one_star)

    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in one_star)

    supplied_subset = bundle.get("one_star_reviews")
    supplied_subset_count = len(supplied_subset) if isinstance(supplied_subset, list) else None
    counts = Counter({
        "raw_cards": len(normalized),
        "one_star_before_deduplication": len(one_star_all),
        "one_star_unique": len(one_star),
        "duplicate_one_star": duplicates,
        "non_one_star": sum(row["rating_value"] not in (None, 1) for row in normalized),
        "unknown_rating": sum(row["rating_value"] is None for row in normalized),
        "missing_review_id": sum(not row.get("review_id") for row in normalized),
        "missing_reviewer": sum(not row.get("reviewer_name") for row in normalized),
        "missing_date": sum(not row.get("published_at") for row in normalized),
        "missing_text": sum(not row.get("review_text") for row in normalized),
    })
    benchmark = args.benchmark_one_star_count
    manifest = {
        "created_at_utc": utc_now(),
        "source_bundle": str(source),
        "source_bundle_sha256": sha256_file(source),
        "schema_version": bundle.get("schema_version"),
        "listing": listing,
        "collection": collection,
        "counts": dict(counts),
        "supplied_one_star_subset_count": supplied_subset_count,
        "derived_subset_count_matches_bundle": (
            supplied_subset_count == len(one_star) if supplied_subset_count is not None else None
        ),
        "benchmark_one_star_count": benchmark,
        "benchmark_count_match": (
            len(one_star) == benchmark if benchmark is not None else None
        ),
        "outputs": {
            "raw_jsonl": str(raw_path),
            "one_star_jsonl": str(one_path),
            "one_star_csv": str(csv_path),
        },
        "output_sha256": {
            "raw_jsonl": sha256_file(raw_path),
            "one_star_jsonl": sha256_file(one_path),
            "one_star_csv": sha256_file(csv_path),
        },
        "complete": False,
        "completeness_note": (
            "Count comparison is a reconciliation signal only. It does not prove "
            "that Google Maps exposed every historical review. Independently "
            "spot-check source records and explain missing/duplicate records."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
