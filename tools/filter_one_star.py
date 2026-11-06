#!/usr/bin/env python3
"""Derive a one-star evidence file from raw visible Google Maps card captures.

The raw input is never modified. Missing fields remain blank; records with
unknown ratings are counted separately and never promoted into the one-star set.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


FIELDS = [
    "review_id", "capture_key", "reviewer_name", "reviewer_profile_url",
    "rating_label", "rating_value", "published_at", "review_text",
    "owner_reply_text", "owner_reply_date", "listing_title", "listing_url",
    "collected_at_utc", "collector",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def record_key(row):
    key = row.get("review_id") or row.get("capture_key")
    if key:
        return str(key)
    material = "|".join(str(row.get(k) or "") for k in (
        "reviewer_name", "published_at", "review_text", "rating_label"
    ))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Raw collector JSONL")
    parser.add_argument("--out", default="output/one-star-reviews")
    args = parser.parse_args()

    source = Path(args.input)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path = output.with_suffix(".jsonl")
    csv_path = output.with_suffix(".csv")
    manifest_path = output.with_suffix(".manifest.json")

    counts = Counter()
    seen = set()
    one_star = []
    malformed = []

    with source.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("record is not a JSON object")
            except Exception as exc:
                malformed.append({"line": line_no, "error": str(exc)})
                continue

            counts["raw_records"] += 1
            rating = row.get("rating_value")
            if rating is None:
                counts["unknown_rating"] += 1
                continue
            try:
                rating = float(rating)
            except (TypeError, ValueError):
                counts["invalid_rating"] += 1
                continue

            if rating != 1.0:
                counts["non_one_star"] += 1
                continue

            key = record_key(row)
            if key in seen:
                counts["duplicate_one_star"] += 1
                continue
            seen.add(key)
            counts["one_star_unique"] += 1
            one_star.append(row)

    with jsonl_path.open("w", encoding="utf-8", newline="") as handle:
        for row in one_star:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in one_star:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    manifest = {
        "created_at_utc": utc_now(),
        "input_file": str(source),
        "one_star_jsonl": str(jsonl_path),
        "one_star_csv": str(csv_path),
        "counts": dict(counts),
        "malformed_lines": malformed,
        "complete": False,
        "completeness_note": (
            "This is a derived filter of the supplied raw capture, not proof "
            "that Google Maps exposed every historical review."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
