#!/usr/bin/env python3
"""Collect one-star Google Maps reviews via Stophy, preserving audit provenance.

This script deliberately does not discover dealerships or guess Place IDs.
The caller must supply a Place ID verified against the dealership's official
America's Car-Mart location page and its linked Google Maps listing.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import pathlib
import sys
import time
from typing import Any

import requests

API_URL = "https://api.stophy.dev/v1/google/maps/reviews"
OUT = pathlib.Path(os.getenv("OUTPUT_DIR", "output"))
FIELDS = [
    "place_id", "listing_url", "review_id", "rating", "review_text",
    "reviewer_name", "published_at", "review_url", "owner_reply_text",
    "owner_reply_at", "language", "author_url", "author_reviews",
    "author_photos", "author_is_local_guide", "collected_at_utc", "page_number",
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def first_value(obj: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def main() -> int:
    place_id = os.getenv("STOPHY_PLACE_ID", "").strip()
    listing_url = os.getenv("STOPHY_LISTING_URL", "").strip()
    api_key = os.getenv("STOPHY_API_KEY", "").strip()
    max_pages = int(os.getenv("STOPHY_MAX_PAGES", "1"))
    delay = float(os.getenv("STOPHY_PAGE_DELAY_SECONDS", "1"))

    if not place_id:
        print("ERROR: STOPHY_PLACE_ID is required; do not guess a Place ID.", file=sys.stderr)
        return 2
    if max_pages < 1 or max_pages > 100:
        print("ERROR: STOPHY_MAX_PAGES must be between 1 and 100.", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    if api_key:
        session.headers["Authorization"] = f"Bearer {api_key}"

    cursor = None
    seen_cursors: set[str] = set()
    rows: list[dict[str, Any]] = []
    page_log: list[dict[str, Any]] = []
    pagination_complete = False
    stopped_reason = "page_limit_reached"
    errors: list[str] = []

    for page_no in range(1, max_pages + 1):
        payload: dict[str, Any] = {"placeId": place_id, "sort": "lowest"}
        if cursor:
            payload["cursor"] = cursor
        try:
            response = session.post(API_URL, json=payload, timeout=60)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            errors.append(f"page {page_no}: {type(exc).__name__}: {exc}")
            stopped_reason = "request_or_parse_error"
            break

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            errors.append(f"page {page_no}: response missing object at data")
            stopped_reason = "unexpected_response_shape"
            break

        results = data.get("results") or []
        if not isinstance(results, list):
            errors.append(f"page {page_no}: data.results was not a list")
            stopped_reason = "unexpected_response_shape"
            break

        collected_at = utc_now()
        one_star_count = 0
        for item in results:
            if not isinstance(item, dict):
                continue
            rating = first_value(item, "rating", "stars")
            try:
                is_one_star = float(rating) == 1.0
            except (TypeError, ValueError):
                is_one_star = False
            if not is_one_star:
                continue
            one_star_count += 1
            rows.append({
                "place_id": place_id,
                "listing_url": listing_url,
                "review_id": first_value(item, "reviewId", "review_id"),
                "rating": rating,
                "review_text": first_value(item, "text", "reviewText"),
                "reviewer_name": first_value(item, "authorName", "author_name"),
                "published_at": first_value(item, "publishedAt", "published_at"),
                "review_url": first_value(item, "reviewUrl", "review_url"),
                "owner_reply_text": first_value(item, "ownerReplyText", "owner_reply_text"),
                "owner_reply_at": first_value(item, "ownerReplyAt", "owner_reply_at"),
                "language": item.get("language"),
                "author_url": first_value(item, "authorUrl", "author_url"),
                "author_reviews": first_value(item, "authorReviews", "author_reviews"),
                "author_photos": first_value(item, "authorPhotos", "author_photos"),
                "author_is_local_guide": first_value(item, "authorIsLocalGuide", "author_is_local_guide"),
                "collected_at_utc": collected_at,
                "page_number": page_no,
            })

        next_cursor = data.get("cursor")
        page_log.append({
            "page": page_no,
            "returned_reviews": len(results),
            "one_star_reviews": one_star_count,
            "has_next_cursor": bool(next_cursor),
            "http_status": response.status_code,
        })

        if not next_cursor:
            pagination_complete = True
            stopped_reason = "pagination_exhausted"
            break
        if not isinstance(next_cursor, str):
            errors.append(f"page {page_no}: cursor was not a string")
            stopped_reason = "invalid_cursor"
            break
        if next_cursor in seen_cursors:
            errors.append(f"page {page_no}: repeated cursor; stopping to avoid loop")
            stopped_reason = "repeated_cursor"
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
        if page_no < max_pages:
            time.sleep(max(0, delay))

    jsonl_path = OUT / "reviews.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_path = OUT / "reviews.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "project": "America's Car-Mart review audit",
        "place_id": place_id,
        "listing_url": listing_url,
        "sort_order": "lowest",
        "filter": "rating == 1",
        "started_at_utc": page_log[0].get("started_at_utc") if page_log else None,
        "finished_at_utc": utc_now(),
        "pages_requested_max": max_pages,
        "pages_fetched": len(page_log),
        "reviews_returned_total": sum(p["returned_reviews"] for p in page_log),
        "one_star_reviews_captured": len(rows),
        "pagination_complete": pagination_complete,
        "complete": pagination_complete and not errors,
        "stopped_reason": stopped_reason,
        "errors": errors,
        "pages": page_log,
        "limitations": [
            "Only reviews returned by the source API were inspected.",
            "The lowest sort order is not itself a one-star filter; rating==1 was applied locally.",
            "A configured page cap produces an incomplete run unless pagination ended before the cap.",
            "Review content is user-generated and has not been independently verified.",
        ],
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
