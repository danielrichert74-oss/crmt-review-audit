#!/usr/bin/env python3
"""Experimental visible-browser collector for one public Google Maps listing.

This deliberately uses the rendered Google Maps interface, not private RPCs,
undocumented endpoints, proxies, or authentication bypasses. It is a pilot
instrument: its output is NEVER marked complete solely because scrolling stops.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def now():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def stable_id(card):
    rid = card.get("review_id")
    if rid:
        return rid
    material = "|".join([
        card.get("reviewer_name", ""),
        card.get("published_at", ""),
        card.get("review_text", ""),
        card.get("rating_label", ""),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def extract_visible_cards(page):
    return page.evaluate("""() => {
      const cards = [...document.querySelectorAll('[data-review-id], .jftiEf')];
      return cards.map((el) => {
        const txt = (s) => {
          const n = el.querySelector(s);
          return n ? (n.innerText || n.textContent || '').trim() : '';
        };
        const ratingNode = el.querySelector('[role="img"][aria-label*="star"], [aria-label*="star"]');
        const ratingLabel = ratingNode ? (ratingNode.getAttribute('aria-label') || '') : '';
        const reviewText = txt('.wiI7pd') || txt('[data-expandable-section]');
        const response = el.querySelector('.CDe7pd, [class*="owner-response"], [class*="reply"]');
        const authorLink = el.querySelector('a[href*="/contrib/"]');
        return {
          review_id: el.getAttribute('data-review-id') || '',
          reviewer_name: txt('.d4r55') || txt('[class*="d4r55"]'),
          reviewer_profile_url: authorLink ? authorLink.href : '',
          rating_label: ratingLabel,
          published_at: txt('.rsqaWe') || txt('[class*="rsqaWe"]'),
          review_text: reviewText,
          owner_reply_text: response ? (response.innerText || response.textContent || '').trim() : '',
          card_text: (el.innerText || '').trim()
        };
      });
    }""") or []


def choose_reviews(page):
    candidates = [
        page.locator('button[aria-label*="Reviews"]').first,
        page.get_by_role("tab", name=re.compile("reviews", re.I)).first,
        page.get_by_text(re.compile(r"^\s*Reviews\s*$", re.I)).first,
    ]
    for item in candidates:
        try:
            if item.count() and item.is_visible():
                item.click(timeout=2500)
                page.wait_for_timeout(1500)
                return True
        except Exception:
            pass
    return False


def choose_lowest(page):
    """Select Lowest and verify the menu exposes it as the active sort.

    Google Maps changes its DOM frequently. Fail closed when the interface
    does not expose a positive selected-state signal.
    """
    sort_candidates = [
        page.locator('button[aria-label*="Sort"]').first,
        page.get_by_role("button", name=re.compile("sort", re.I)).first,
        page.get_by_text(re.compile(r"Most relevant|Newest|Highest|Lowest", re.I)).first,
    ]
    opened = False
    for item in sort_candidates:
        try:
            if item.count() and item.is_visible():
                item.click(timeout=2500)
                page.wait_for_timeout(500)
                opened = True
                break
        except Exception:
            pass
    if not opened:
        return {"verified": False, "evidence": "sort-control-not-found"}

    try:
        option = page.get_by_text(re.compile(r"^\\s*Lowest\\s*$", re.I)).last
        if not option.count() or not option.is_visible():
            return {"verified": False, "evidence": "lowest-option-not-visible"}
        option.click(timeout=4000)
        page.wait_for_timeout(1200)
    except Exception as exc:
        return {"verified": False, "evidence": "lowest-click-failed: " + str(exc)[:240]}

    # Reopen the sort menu and inspect an explicit selected-state attribute.
    for item in sort_candidates:
        try:
            if item.count() and item.is_visible():
                item.click(timeout=2500)
                page.wait_for_timeout(400)
                break
        except Exception:
            continue

    try:
        evidence = page.evaluate("""() => {
          const norm = s => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
          const nodes = [...document.querySelectorAll('[role="menuitemradio"], [role="option"], [aria-checked], [aria-selected]')];
          const lowest = nodes.filter(n => norm(n.innerText || n.textContent) === 'lowest');
          return lowest.map(n => ({
            role: n.getAttribute('role') || '',
            ariaChecked: n.getAttribute('aria-checked'),
            ariaSelected: n.getAttribute('aria-selected'),
            dataSelected: n.getAttribute('data-selected'),
            className: String(n.className || '').slice(0, 160)
          }));
        }""")
    except Exception:
        evidence = []

    verified = any(
        str(item.get("ariaChecked", "")).lower() == "true"
        or str(item.get("ariaSelected", "")).lower() == "true"
        or str(item.get("dataSelected", "")).lower() == "true"
        for item in evidence
    )
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return {
        "verified": verified,
        "evidence": evidence if evidence else "no-explicit-selected-state-exposed"
    }


def find_scroll_container(page):
    return page.evaluate("""() => {
      const card = document.querySelector('[data-review-id], .jftiEf');
      if (!card) return null;
      let node = card.parentElement;
      while (node && node !== document.body) {
        const s = getComputedStyle(node);
        const canScroll = /(auto|scroll)/.test(s.overflowY) &&
          node.scrollHeight > node.clientHeight + 30;
        if (canScroll) return {
          tag: node.tagName, id: node.id || '',
          className: String(node.className || '').slice(0, 300),
          role: node.getAttribute('role') || '',
          height: node.clientHeight, scrollHeight: node.scrollHeight
        };
        node = node.parentElement;
      }
      const feed = document.querySelector('[role="feed"]');
      if (feed) return {
        tag: feed.tagName, id: feed.id || '',
        className: String(feed.className || '').slice(0, 300),
        role: 'feed', height: feed.clientHeight, scrollHeight: feed.scrollHeight
      };
      return null;
    }""")


def scroll_feed(page):
    return page.evaluate("""() => {
      const card = document.querySelector('[data-review-id], .jftiEf');
      if (!card) return {ok:false, reason:'no-review-card'};
      let node = card.parentElement;
      while (node && node !== document.body) {
        const s = getComputedStyle(node);
        if (/(auto|scroll)/.test(s.overflowY) &&
            node.scrollHeight > node.clientHeight + 30) {
          const before = node.scrollTop;
          node.scrollTop = Math.min(node.scrollTop + Math.max(500, node.clientHeight * 0.8),
                                    node.scrollHeight);
          node.dispatchEvent(new Event('scroll', {bubbles:true}));
          return {ok:true, before, after:node.scrollTop,
                  clientHeight:node.clientHeight, scrollHeight:node.scrollHeight};
        }
        node = node.parentElement;
      }
      const feed = document.querySelector('[role="feed"]');
      if (feed) {
        const before = feed.scrollTop;
        feed.scrollTop += Math.max(500, feed.clientHeight * 0.8);
        feed.dispatchEvent(new Event('scroll', {bubbles:true}));
        return {ok:true, before, after:feed.scrollTop,
                clientHeight:feed.clientHeight, scrollHeight:feed.scrollHeight};
      }
      return {ok:false, reason:'scroll-container-not-found'};
    }""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="Exact dealership name and street address")
    ap.add_argument("--out", default="output/local-browser-capture.jsonl")
    ap.add_argument("--max-rounds", type=int, default=250)
    ap.add_argument("--headed", action="store_true", help="Show the browser window")
    ap.add_argument("--slow-mo", type=int, default=0)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    search_url = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(args.query)
    captured = {}
    trace = []
    run_started = now()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, slow_mo=args.slow_mo)
        context = browser.new_context(locale="en-US", viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        try:
            page.get_by_role("button", name=re.compile("Accept all|Reject all", re.I)).first.click(timeout=1500)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        # The search result must be selected explicitly; do not scrape an
        # address-only map pin or silently accept the first unrelated result.
        try:
            page.get_by_text(re.compile(re.escape(args.query.split(",")[0]), re.I)).first.click(timeout=8000)
            page.wait_for_timeout(2500)
        except Exception:
            pass

        listing_title = ""
        try:
            listing_title = clean(page.locator("h1").first.inner_text(timeout=1500))
        except Exception:
            pass
        # Fail closed if Google did not open the intended business profile.
        # The exact title check is a minimum identity gate, not full address
        # verification; the manifest preserves the title and URL for review.
        normalized_title = re.sub(r"[^a-z0-9]", "", listing_title.lower())
        identity_verified = "carmart" in normalized_title and "greenville" in normalized_title
        listing_url = page.url

        opened_reviews = choose_reviews(page) if identity_verified else False
        sort_check = choose_lowest(page) if opened_reviews else {"verified": False, "evidence": "reviews-not-opened"}
        lowest_selected = bool(sort_check.get("verified"))
        if not identity_verified:
            print(
                f"STOP: listing title did not verify as CAR-MART of Greenville: {listing_title!r}",
                file=sys.stderr
            )
        elif not opened_reviews:
            print("STOP: could not positively open the listing's Reviews panel.", file=sys.stderr)
        if identity_verified and not lowest_selected:
            print("STOP: could not positively select Lowest sorting.", file=sys.stderr)
        scroll_meta = find_scroll_container(page)
        stable_rounds = 0
        previous_count = 0
        stop_reason = "max-rounds-reached"

        if opened_reviews and lowest_selected:
            for round_no in range(args.max_rounds):
                batch = extract_visible_cards(page)
                new_this_round = 0
                for item in batch:
                    rating = re.search(r"([1-5](?:\.\d+)?)\s*star", item.get("rating_label", ""), re.I)
                    if rating:
                        item["rating_value"] = float(rating.group(1))
                    else:
                        item["rating_value"] = None
                    item["collected_at_utc"] = now()
                    item["listing_title"] = listing_title
                    item["listing_url"] = listing_url
                    item["collector"] = "crmt-local-playwright-visible-ui"
                    key = stable_id(item)
                    if key not in captured:
                        item["capture_key"] = key
                        captured[key] = item
                        new_this_round += 1

                total = len(captured)
                movement = scroll_feed(page)
                trace.append({
                    "round": round_no + 1, "visible_cards": len(batch),
                    "new_unique_cards": new_this_round, "total_unique": total,
                    "scroll": movement, "timestamp_utc": now()
                })
                if total == previous_count and new_this_round == 0:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                previous_count = total

                if stable_rounds >= 10:
                    stop_reason = "no-new-unique-review-cards-for-10-rounds"
                    break
                if not movement.get("ok"):
                    stop_reason = movement.get("reason", "scroll-failed")
                    break
                if movement.get("after") == movement.get("before") and stable_rounds >= 3:
                    stop_reason = "scroll-position-stalled"
                    break
                page.wait_for_timeout(1100)

        # Save all captured cards, including non-one-star records, as raw
        # collection evidence. A separate processor filters 1-star records.
        with out.open("w", encoding="utf-8") as handle:
            for item in captured.values():
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

        manifest = {
            "started_at_utc": run_started, "finished_at_utc": now(),
            "query": args.query, "listing_title": listing_title,
            "identity_verified_by_title": identity_verified,
            "listing_url": listing_url, "opened_reviews": opened_reviews,
            "selected_lowest": lowest_selected, "sort_verification": sort_check.get("evidence"),
            "scroll_container": scroll_meta,
            "unique_cards_captured": len(captured),
            "one_star_cards_captured": sum(1 for x in captured.values() if x.get("rating_value") == 1.0),
            "stop_reason": stop_reason, "rounds": len(trace),
            "complete": False,
            "completeness_note": "Experimental UI capture only. Stopping is not proof of end-of-list or complete historical coverage.",
            "trace": trace
        }
        manifest_path = out.with_suffix(".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({k:v for k,v in manifest.items() if k != "trace"}, indent=2))
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
