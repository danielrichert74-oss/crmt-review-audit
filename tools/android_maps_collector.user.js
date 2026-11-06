// ==UserScript==
// @name         CRMT Google Maps Review Capture (Android pilot)
// @namespace    https://github.com/danielrichert74-oss/crmt-review-audit
// @version      0.1.0
// @description  User-controlled capture of visible public Google Maps review cards; exports raw and one-star evidence.
// @match        https://www.google.com/maps/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(() => {
  "use strict";

  const EXPECTED = {
    titleTokens: ["car-mart", "greenville"],
    address: "5107 Interstate Highway 30, Greenville, TX 75402",
    phone: "903-458-9900"
  };
  const cards = new Map();
  let armed = false;
  let verifiedIdentity = null;
  let sortVerificationMethod = null;
  let observer = null;
  let lastCapture = null;

  const clean = value => String(value || "").replace(/\s+/g, " ").trim();
  const digits = value => String(value || "").replace(/\D/g, "");
  const norm = value => clean(value).toLowerCase();
  const hash = value => "local-" + value;

  const panel = document.createElement("section");
  panel.id = "crmt-review-capture-panel";
  panel.style.cssText = [
    "position:fixed", "z-index:2147483647", "right:8px", "bottom:12px",
    "width:min(340px,calc(100vw - 16px))", "max-height:58vh",
    "overflow:auto", "background:#101820", "color:#fff",
    "border:2px solid #6da9d2", "border-radius:12px",
    "padding:10px", "font:14px/1.35 system-ui,sans-serif",
    "box-shadow:0 3px 18px #0008"
  ].join(";");
  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;gap:8px;align-items:center">
      <strong>CRMT review capture</strong>
      <button data-action="hide" style="font-size:18px">−</button>
    </div>
    <div data-status style="margin:8px 0">Waiting for a Google Maps business profile.</div>
    <div data-count style="margin:6px 0">0 captured · 0 one-star</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
      <button data-action="identity">Verify business</button>
      <button data-action="verify">Arm (Lowest detected)</button>
      <button data-action="manual">Arm (Lowest confirmed visually)</button>
      <button data-action="capture">Capture visible</button>
      <button data-action="scroll">Scroll feed once</button>
      <button data-action="raw">Export raw JSONL</button>
      <button data-action="one">Export one-star JSONL</button>
      <button data-action="csv">Export one-star CSV</button>
      <button data-action="manifest">Export manifest</button>
    </div>
    <div style="margin-top:7px;font-size:11px;opacity:.8">
      User-controlled pilot. Select Lowest in Google Maps first. This tool never claims complete history.
    </div>`;
  const styleButtons = () => panel.querySelectorAll("button").forEach(b => {
    b.style.cssText = "min-height:38px;padding:6px;border:1px solid #9ab;border-radius:7px;background:#e8f0f6;color:#102030;font-weight:600";
  });
  (document.body || document.documentElement).appendChild(panel);
  styleButtons();

  const status = message => { panel.querySelector("[data-status]").textContent = message; };
  const updateCount = () => {
    const values = [...cards.values()];
    panel.querySelector("[data-count]").textContent =
      values.length + " captured · " +
      values.filter(x => x.rating_value === 1).length + " one-star";
  };

  function identityCheck() {
    const title = clean(document.querySelector("h1")?.innerText);
    const ariaText = [...document.querySelectorAll("[aria-label]")]
      .map(node => node.getAttribute("aria-label") || "").join(" ");
    const body = clean((document.body?.innerText || "") + " " + ariaText);
    const titleOk = EXPECTED.titleTokens.every(t => norm(title).includes(norm(t)));
    const bodyNormalized = norm(body).replace(/[^a-z0-9]/g, "");
    const addressOk = (EXPECTED.address.toLowerCase().match(/[a-z0-9]+/g) || [])
      .filter(x => x.length > 1).every(t => bodyNormalized.includes(t));
    const phoneOk = digits(body).includes(digits(EXPECTED.phone));
    return { ok: titleOk && addressOk && phoneOk, title, titleOk, addressOk, phoneOk };
  }

  function lowestCheck() {
    const nodes = [...document.querySelectorAll(
      '[role="menuitemradio"],[role="option"],[aria-checked="true"],[aria-selected="true"]'
    )];
    const selected = nodes.some(n =>
      norm(n.innerText || n.textContent) === "lowest" &&
      (n.getAttribute("aria-checked") === "true" ||
       n.getAttribute("aria-selected") === "true")
    );
    const labels = [...document.querySelectorAll('button[aria-label]')]
      .map(n => norm(n.getAttribute("aria-label")));
    const buttonLabel = labels.some(x => x.includes("sort") && x.includes("lowest"));
    return selected || buttonLabel;
  }

  function extractCard(el) {
    const get = selector => clean(el.querySelector(selector)?.innerText ||
      el.querySelector(selector)?.textContent || "");
    const ratingNode = el.querySelector('[role="img"][aria-label*="star"],[aria-label*="star"]');
    const ratingLabel = ratingNode?.getAttribute("aria-label") || "";
    const ratingMatch = ratingLabel.match(/([1-5](?:\.\d+)?)\s*star/i);
    const response = el.querySelector(".CDe7pd,[class*='owner-response'],[class*='reply']");
    const responseDate = response?.querySelector("[class*='date'],[class*='time'],[aria-label*='ago']");
    const author = el.querySelector('a[href*="/contrib/"]');
    const cardText = clean(el.innerText || el.textContent || "");
    const dateMatch = cardText.match(/\\b(?:\\d+ (?:day|week|month|year)s? ago|\\w+ \\d{1,2}, \\d{4})\\b/i);
    const row = {
      review_id: el.getAttribute("data-review-id") || "",
      reviewer_name: get(".d4r55"),
      reviewer_profile_url: author?.href || "",
      rating_label: ratingLabel,
      rating_value: ratingMatch ? Number(ratingMatch[1]) : null,
      published_at: get(".rsqaWe") || (dateMatch ? dateMatch[0] : ""),
      review_text: get(".wiI7pd") || get("[data-expandable-section]"),
      owner_reply_text: clean(response?.innerText || response?.textContent || ""),
      owner_reply_date: clean(responseDate?.getAttribute("aria-label") ||
        responseDate?.innerText || responseDate?.textContent || ""),
      listing_title: verifiedIdentity?.title || clean(document.querySelector("h1")?.innerText),
      listing_url: verifiedIdentity?.listing_url_at_verification || location.href,
      collected_at_utc: new Date().toISOString(),
      collector: "crmt-android-userscript-pilot",
      card_text: cardText
    };
    const keyMaterial = [
      row.reviewer_name, row.published_at, row.review_text, row.rating_label
    ].join("|");
    row.capture_key = row.review_id || hash(keyMaterial);
    return row;
  }

  function captureVisible() {
    if (!armed) {
      status("Not armed. Verify the business identity and Lowest sort first.");
      return;
    }
    const currentTitle = clean(document.querySelector("h1")?.innerText);
    const currentPageText = norm((document.body?.innerText || "") + " " +
      [...document.querySelectorAll("[aria-label]")]
        .map(node => node.getAttribute("aria-label") || "").join(" "));
    const sameBusinessStillVisible = verifiedIdentity &&
      EXPECTED.titleTokens.every(token =>
        norm(currentTitle).includes(norm(token)) ||
        currentPageText.includes(norm(token))
      );
    if (!sameBusinessStillVisible) {
      armed = false;
      status("STOP: the verified business name is no longer visible. Re-check the listing before continuing.");
      return;
    }
    const visible = [...document.querySelectorAll("[data-review-id],.jftiEf")];
    let added = 0;
    for (const el of visible) {
      for (const button of el.querySelectorAll("button,[role='button']")) {
        const label = clean((button.getAttribute("aria-label") || "") + " " +
          (button.innerText || button.textContent || ""));
        if (/^more$/i.test(label)) {
          try { button.click(); } catch (_) {}
        }
      }
      const row = extractCard(el);
      if (!cards.has(row.capture_key)) {
        cards.set(row.capture_key, row);
        added++;
      }
    }
    lastCapture = new Date().toISOString();
    updateCount();
    status("Captured " + added + " new card(s); " + visible.length + " currently visible.");
  }

  function scrollOnce() {
    if (!armed) return status("Verify and arm before scrolling.");
    const card = document.querySelector("[data-review-id],.jftiEf");
    if (!card) return status("No review card is visible yet.");
    let node = card.parentElement;
    while (node && node !== document.body) {
      const css = getComputedStyle(node);
      if (/(auto|scroll)/.test(css.overflowY) && node.scrollHeight > node.clientHeight + 30) {
        const before = node.scrollTop;
        node.scrollTop = Math.min(before + Math.max(450, node.clientHeight * 0.75), node.scrollHeight);
        node.dispatchEvent(new Event("scroll", { bubbles: true }));
        captureVisible();
        return status("Feed scrolled " + Math.round(node.scrollTop - before) + " px. Capture again after loading settles.");
      }
      node = node.parentElement;
    }
    const feed = document.querySelector('[role="feed"]');
    if (feed) {
      const before = feed.scrollTop;
      feed.scrollTop += Math.max(450, feed.clientHeight * 0.75);
      feed.dispatchEvent(new Event("scroll", { bubbles: true }));
      captureVisible();
      return status("Feed scroll attempted. Capture again after loading settles.");
    }
    status("Could not identify the review feed. Scroll manually, then tap Capture visible.");
  }

  function download(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  function exportRaw() {
    const rows = [...cards.values()];
    download("crmt-greenville-raw-" + Date.now() + ".jsonl",
      rows.map(x => JSON.stringify(x)).join("\n") + (rows.length ? "\n" : ""),
      "application/x-ndjson");
  }

  function exportOneStar() {
    const rows = [...cards.values()].filter(x => x.rating_value === 1);
    download("crmt-greenville-one-star-" + Date.now() + ".jsonl",
      rows.map(x => JSON.stringify(x)).join("\n") + (rows.length ? "\n" : ""),
      "application/x-ndjson");
  }

  function csvCell(value) {
    const text = value == null ? "" : String(value);
    return '"' + text.replace(/"/g, '""') + '"';
  }
  function exportCsv() {
    const rows = [...cards.values()].filter(x => x.rating_value === 1);
    const fields = [
      "review_id", "capture_key", "reviewer_name", "reviewer_profile_url",
      "rating_label", "rating_value", "published_at", "review_text",
      "owner_reply_text", "owner_reply_date", "listing_title", "listing_url", "collected_at_utc", "card_text"
    ];
    const csv = [fields.join(","),
      ...rows.map(row => fields.map(f => csvCell(row[f])).join(","))
    ].join("\r\n");
    download("crmt-greenville-one-star-" + Date.now() + ".csv", csv, "text/csv");
  }

  panel.addEventListener("click", event => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const action = button.dataset.action;
    if (action === "hide") {
      panel.style.width = "42px";
      panel.style.height = "42px";
      panel.style.overflow = "hidden";
      panel.innerHTML = '<button data-action="show" style="width:32px;height:32px">CR</button>';
    } else if (action === "show") {
      location.reload();
    } else if (action === "identity") {
      const identity = identityCheck();
      armed = false;
      if (!identity.ok) {
        verifiedIdentity = null;
        status("IDENTITY FAIL — title:" + identity.titleOk +
          ", address:" + identity.addressOk + ", phone:" + identity.phoneOk +
          ". Verify the business on its overview page before opening Reviews.");
      } else {
        verifiedIdentity = {
          ...identity,
          verified_at_utc: new Date().toISOString(),
          listing_url_at_verification: location.href
        };
        status("Business identity verified on overview: " + identity.title +
          ". Now open Reviews and choose Lowest.");
      }
    } else if (action === "verify") {
      const hasReviewCards = document.querySelector("[data-review-id],.jftiEf");
      if (!verifiedIdentity || !hasReviewCards) {
        armed = false;
        status("First verify the business on its overview page, then open Reviews.");
      } else if (!lowestCheck()) {
        armed = false;
        status("Business identity is verified. Select Lowest, then retry or use the visual confirmation button.");
      } else {
        armed = true;
        sortVerificationMethod = "dom-selected-state";
        status("Armed for " + verifiedIdentity.title + ". Lowest sort state detected.");
        captureVisible();
      }
    } else if (action === "manual") {
      const hasReviewCards = document.querySelector("[data-review-id],.jftiEf");
      if (!verifiedIdentity || !hasReviewCards) {
        armed = false;
        status("Manual arm refused: verify the business overview first and open Reviews.");
      } else {
        armed = true;
        sortVerificationMethod = "user-visually-confirmed";
        status("Manually armed for " + verifiedIdentity.title +
          ". You confirmed Lowest is visibly selected. Capture and scroll carefully.");
        captureVisible();
      }
    } else if (action === "capture") captureVisible();
    else if (action === "scroll") scrollOnce();
    else if (action === "raw") exportRaw();
    else if (action === "one") exportOneStar();
    else if (action === "csv") exportCsv();
    else if (action === "manifest") {
      const rows = [...cards.values()];
      const identity = verifiedIdentity;
      download("crmt-greenville-manifest-" + Date.now() + ".json",
        JSON.stringify({
          created_at_utc: new Date().toISOString(),
          listing_title: identity?.title || "",
          listing_url_at_verification: identity?.listing_url_at_verification || "",
          listing_url_at_export: location.href,
          identity_checks: identity,
          lowest_selected_at_arm: true,
          lowest_verification_method: sortVerificationMethod,
          raw_cards_captured: rows.length,
          one_star_cards_captured: rows.filter(x => x.rating_value === 1).length,
          last_capture_at_utc: lastCapture, complete: false,
          completeness_note: "User-controlled visible-card capture. No claim of complete historical coverage."
        }, null, 2), "application/json");
    }
  });

  observer = new MutationObserver(records => {
    if (armed && records.some(record => !panel.contains(record.target))) captureVisible();
  });
  observer.observe(document.body, { childList: true, subtree: true });
  status("Open the Greenville business overview and tap Verify business before opening Reviews.");
})();
