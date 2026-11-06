#!/usr/bin/env python3
"""Resolve Greenville on Google Maps, then capture one-star reviews from Stophy."""
import csv, datetime as dt, json, os, pathlib, re, sys, time
import requests
BASE="https://api.stophy.dev/v1/google/maps"
OUT=pathlib.Path(os.getenv("OUTPUT_DIR","output"))
FIELDS=["place_id","listing_url","review_id","rating","review_text","reviewer_name","published_at","review_url","owner_reply_text","owner_reply_at","language","author_url","author_reviews","author_photos","author_is_local_guide","collected_at_utc","page_number"]
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def norm(s): return re.sub(r"[^a-z0-9]+","",str(s or "").lower())
def pick(o,*ks):
    for k in ks:
        if o.get(k) not in (None,""): return o[k]
    return None
def main():
    expected={"name":os.getenv("STOPHY_EXPECTED_NAME","CAR-MART of Greenville"),"address":os.getenv("STOPHY_EXPECTED_ADDRESS","5107 Interstate Highway 30, Greenville, TX 75402"),"phone":os.getenv("STOPHY_EXPECTED_PHONE","903-458-9900")}
    query=os.getenv("STOPHY_QUERY","America's Car-Mart"); location=os.getenv("STOPHY_LOCATION","Greenville, TX")
    max_pages=int(os.getenv("STOPHY_MAX_PAGES","1")); key=os.getenv("STOPHY_API_KEY","").strip()
    if not 1<=max_pages<=100: print("STOPHY_MAX_PAGES must be 1..100",file=sys.stderr); return 2
    OUT.mkdir(parents=True,exist_ok=True); s=requests.Session()
    s.headers.update({"Accept":"application/json","Content-Type":"application/json"})
    if key: s.headers["Authorization"]="Bearer "+key
    started=now(); errors=[]; pages=[]; rows=[]; complete=False; stopped="page_limit_reached"
    try:
        r=s.post(BASE+"/search",json={"query":query,"location":location,"country":"us"},timeout=60); r.raise_for_status()
        candidates=(r.json().get("data") or {}).get("results") or []
    except Exception as e: candidates=[]; errors.append("Maps search: "+repr(e))
    phone=norm(expected["phone"]); matches=[]
    for c in candidates:
        cp=norm(c.get("phone")); name=norm(c.get("name")); addr=norm(c.get("address"))
        phone_ok=bool(phone and cp and (phone in cp or cp in phone))
        name_addr_ok=("greenville" in name and ("car" in name or "mart" in name) and "greenville" in addr and "5107" in addr)
        if phone_ok or name_addr_ok: matches.append(c)
    place=matches[0] if len(matches)==1 else {}
    if len(matches)!=1:
        errors.append(f"Expected exactly one Greenville match; found {len(matches)}. No reviews requested.")
        stopped="place_resolution_not_unique"
    place_id=pick(place,"googlePlaceId","placeId"); place_url=pick(place,"placeUrl")
    if not errors and not (place_id or place_url):
        errors.append("Resolved result lacks a place identifier and place URL."); stopped="missing_place_identifier"
    cursor=None; seen=set()
    if not errors:
        for page in range(1,max_pages+1):
            payload={"sort":"lowest"}
            if place_id: payload["placeId"]=place_id
            else: payload["placeUrl"]=place_url
            if cursor: payload["cursor"]=cursor
            try:
                rr=s.post(BASE+"/reviews",json=payload,timeout=60); rr.raise_for_status(); body=rr.json()
            except Exception as e: errors.append(f"Reviews page {page}: "+repr(e)); stopped="request_error"; break
            data=body.get("data") if isinstance(body,dict) else None
            if not isinstance(data,dict) or not isinstance(data.get("results"),list):
                errors.append(f"Reviews page {page}: unexpected response shape"); stopped="unexpected_response_shape"; break
            results=data["results"]; stamp=now(); one=0
            for x in results:
                if not isinstance(x,dict): continue
                rating=pick(x,"rating","stars")
                try: is_one=float(rating)==1.0
                except (ValueError,TypeError): is_one=False
                if not is_one: continue
                one+=1
                rows.append({"place_id":place_id or place_url,"listing_url":place_url,"review_id":pick(x,"reviewId","review_id"),"rating":rating,"review_text":pick(x,"text","reviewText"),"reviewer_name":pick(x,"authorName","author_name"),"published_at":pick(x,"publishedAt","published_at"),"review_url":pick(x,"reviewUrl","review_url"),"owner_reply_text":pick(x,"ownerReplyText","owner_reply_text"),"owner_reply_at":pick(x,"ownerReplyAt","owner_reply_at"),"language":x.get("language"),"author_url":pick(x,"authorUrl","author_url"),"author_reviews":pick(x,"authorReviews","author_reviews"),"author_photos":pick(x,"authorPhotos","author_photos"),"author_is_local_guide":pick(x,"authorIsLocalGuide","author_is_local_guide"),"collected_at_utc":stamp,"page_number":page})
            nxt=data.get("cursor"); pages.append({"page":page,"returned_reviews":len(results),"one_star_reviews":one,"has_next_cursor":bool(nxt),"http_status":rr.status_code})
            if not nxt: complete=True; stopped="pagination_exhausted"; break
            if not isinstance(nxt,str) or nxt in seen: errors.append(f"Reviews page {page}: invalid/repeated cursor"); stopped="invalid_or_repeated_cursor"; break
            seen.add(nxt); cursor=nxt
            if page<max_pages: time.sleep(1)
    with (OUT/"reviews.jsonl").open("w",encoding="utf-8") as h:
        for row in rows: h.write(json.dumps(row,ensure_ascii=False)+"\n")
    with (OUT/"reviews.csv").open("w",newline="",encoding="utf-8-sig") as h:
        w=csv.DictWriter(h,fieldnames=FIELDS,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    manifest={"project":"America's Car-Mart review audit","started_at_utc":started,"finished_at_utc":now(),"expected_business":expected,"resolved_place":{"name":place.get("name"),"address":place.get("address"),"phone":place.get("phone"),"website":place.get("website"),"place_id":place_id,"place_url":place_url},"search_candidate_count":len(candidates),"matched_candidate_count":len(matches),"sort_order":"lowest","filter":"rating == 1","pages_requested_max":max_pages,"pages_fetched":len(pages),"reviews_returned_total":sum(p["returned_reviews"] for p in pages),"one_star_reviews_captured":len(rows),"pagination_complete":complete,"complete":complete and not errors,"stopped_reason":stopped,"errors":errors,"pages":pages,"limitations":["Only reviews returned by Stophy were inspected.","Lowest sort is not itself a one-star filter; rating==1 was applied locally.","One-page pilot is incomplete if a cursor remains.","Review statements are user-generated and not independently verified."]}
    (OUT/"run_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2)); return 1 if errors else 0
if __name__=="__main__": raise SystemExit(main())
