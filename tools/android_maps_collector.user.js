// ==UserScript==
// @name         CRMT Google Maps Review Capture (Android pilot)
// @namespace    https://github.com/danielrichert74-oss/crmt-review-audit
// @version      0.5.0
// @description  Persistent, configurable capture of visible public Google Maps review cards; exports raw and one-star evidence.
// @match        https://www.google.com/maps/*
// @match        https://maps.google.com/maps/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(() => {
  "use strict";

  let EXPECTED = {
    titleTokens: ["carmart", "greenville"],
    address: "5107 Interstate Highway 30, Greenville, TX 75402",
    phone: "903-458-9900"
  };
  try {
    const savedConfig = JSON.parse(localStorage.getItem("crmt-review-config-v1") || "null");
    if (savedConfig && Array.isArray(savedConfig.titleTokens) && savedConfig.address && savedConfig.phone) EXPECTED = savedConfig;
  } catch (_) {}
  const cards = new Map();
  let storageKey = "crmt-review-capture-greenville-v1";
  let storageWarning = "";
  function persistCards() {
    try {
      localStorage.setItem(storageKey, JSON.stringify([...cards.values()]));
      storageWarning = "";
    } catch (error) {
      storageWarning = " Local save failed (" + (error?.name || "storage error") + "); export now.";
    }
  }
  function restoreCards() {
    cards.clear();
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "[]");
      if (Array.isArray(saved)) saved.forEach(row => {
        if (row && row.capture_key) cards.set(row.capture_key, row);
      });
    } catch (_) { storageWarning = " Previous local save could not be read."; }
    updateCount();
  }
  let armed = false;
  let verifiedIdentity = null;
  let sortVerificationMethod = null;
  let captureMode = null;
  let observer = null;
  let lastCapture = null;
  let autoTimer = null;
  let autoIdle = 0;
  let autoSteps = 0;
  let autoStartedAt = null;
  let autoFinishedAt = null;
  let autoStopReason = "not-started";
  let autoBundleExported = false;

  const clean = value => String(value || "").replace(/\s+/g, " ").trim();
  const digits = value => String(value || "").replace(/\D/g, "");
  const norm = value => clean(value).toLowerCase();
  const hash = value => {
    let h = 14695981039346656037n;
    for (let i = 0; i < value.length; i++) {
      h ^= BigInt(value.charCodeAt(i));
      h = BigInt.asUintN(64, h * 1099511628211n);
    }
    return "local-" + h.toString(16);
  };

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
      <button data-action="run">RUN AUDIT (all reviews)</button>
      <button data-action="identity">Verify business</button>
      <button data-action="configure">Configure dealership</button>
      <button data-action="verify">Arm (Lowest detected)</button>
      <button data-action="manual">Arm (Lowest confirmed visually)</button>
      <button data-action="unsorted">Arm (Unsorted visible reviews)</button>
      <button data-action="capture">Capture visible</button>
      <button data-action="auto">AUTO-COLLECT feed</button>
      <button data-action="stop">Stop auto-collect</button>
      <button data-action="raw">Export raw JSONL</button>
      <button data-action="one">Export one-star JSONL</button>
      <button data-action="csv">Export one-star CSV</button>
      <button data-action="manifest">Export manifest</button>
    </div>
    <div style="margin-top:7px;font-size:11px;opacity:.8">
      User-controlled pilot. Use Lowest only when visibly selected; otherwise use Unsorted mode. Never claims complete history.
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
    const h1Title = clean(document.querySelector("h1")?.innerText);
    const documentTitle = clean(document.title);
    const ariaText = [...document.querySelectorAll("[aria-label]")]
      .map(node => node.getAttribute("aria-label") || "").join(" ");
    const bodyText = document.body?.innerText || "";
    const bodyContent = document.body?.textContent || "";
    const decodedUrl = (() => {
      try { return decodeURIComponent(location.href); }
      catch (_) { return location.href; }
    })();
    const body = clean([bodyText, bodyContent, ariaText, documentTitle].join(" "));
    const identityText = clean([body, decodedUrl].join(" "));
    const titleCandidates = [h1Title, documentTitle].filter(Boolean);
    const matchingTitle = titleCandidates.find(candidate => {
      const normalized = norm(candidate).replace(/[^a-z0-9]/g, "");
      return EXPECTED.titleTokens.every(token => normalized.includes(token));
    });
    const title = matchingTitle || h1Title || documentTitle;
    const titleOk = Boolean(matchingTitle);
    const bodyNormalized = norm(body).replace(/[^a-z0-9]/g, "");
    const identityNormalized = norm(identityText).replace(/[^a-z0-9]/g, "");
    // On mobile Maps, the address is encoded in the canonical /place/ URL
    // rather than exposed in body text. Validate that URL plus the visible Call link.
    const addressTokens = norm(EXPECTED.address).replace(/[^a-z0-9 ]/g, " ").split(/\s+/)
      .filter(token => token.length >= 3 && !["street", "road", "drive", "avenue", "highway", "interstate", "frontage", "suite", "unit"].includes(token));
    const addressOk = addressTokens.length > 0 &&
      addressTokens.every(token => identityNormalized.includes(token));
    const phoneLinks = [...document.querySelectorAll('a[href^="tel:"]')]
      .map(a => a.href || "");
    const phoneEvidence = digits([body, ...phoneLinks].join(" "));
    const phoneOk = phoneEvidence.includes(digits(EXPECTED.phone));
    return {
      ok: titleOk && addressOk && phoneOk, title, titleOk, addressOk, phoneOk,
      diagnostic: {
        host: location.hostname,
        documentTitle,
        h1Title,
        bodyInnerTextLength: bodyText.length,
        bodyTextContentLength: bodyContent.length,
        hasStreetNumber: identityNormalized.includes("5107"),
        hasGreenville: identityNormalized.includes("greenville"),
        hasTexas: identityNormalized.includes("tx"),
        hasZip: identityNormalized.includes("75402"),
        hasPhone: phoneOk,
        configuredAddressTokens: addressTokens,
        addressEvidenceSource: "visible page text and decoded Google Maps URL",
        phoneEvidenceSource: "visible page text and tel: links",
        currentUrl: location.href,
        matchingLinks: [...document.querySelectorAll("a[href]")]
          .filter(a => /car-mart|tel:/i.test((a.href || "") + " " + (a.innerText || "")))
          .slice(0, 12)
          .map(a => ({ text: clean(a.innerText || a.textContent), href: a.href })),
        bodyTextSample: clean(bodyText).slice(0, 900)
      }
    };
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
    const dateMatch = cardText.match(/\b(?:\d+ (?:day|week|month|year)s? ago|\w+ \d{1,2}, \d{4})\b/i);
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
      status("Not armed. Verify the business identity, then choose a capture mode.");
      return;
    }
    const currentTitle = clean(document.querySelector("h1")?.innerText);
    const currentPageText = norm((document.body?.innerText || "") + " " +
      [...document.querySelectorAll("[aria-label]")]
        .map(node => node.getAttribute("aria-label") || "").join(" "))
        .replace(/[^a-z0-9]/g, "");
    const currentTitleNormalized = norm(currentTitle).replace(/[^a-z0-9]/g, "");
    const sameBusinessStillVisible = verifiedIdentity &&
      EXPECTED.titleTokens.every(token =>
        currentTitleNormalized.includes(token) ||
        currentPageText.includes(token)
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
    if (added) persistCards();
    status("Captured " + added + " new card(s); " + visible.length + " currently visible." + storageWarning);
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

  function stopAuto(message) {
    const wasRunning = Boolean(autoTimer && autoStartedAt);
    if (autoTimer) clearInterval(autoTimer);
    autoTimer = null;
    autoFinishedAt = new Date().toISOString();
    autoStopReason = message || "stopped-by-user";
    status(message || ("Auto-collect stopped. " + cards.size + " unique reviews captured."));
    if (wasRunning && !autoBundleExported) exportAuditBundle();
  }

  function restoreVerifiedListing(identity) {
    const nextStorageKey = "crmt-review-capture-" + hash(location.href.split("?")[0]).slice(6) + "-v1";
    if (nextStorageKey !== storageKey) {
      storageKey = nextStorageKey;
      restoreCards();
    }
    verifiedIdentity = {
      ...identity,
      verified_at_utc: new Date().toISOString(),
      listing_url_at_verification: location.href
    };
  }

  function clickReviewsTab() {
    const candidates = [...document.querySelectorAll('button,[role="tab"],[role="button"],a')];
    const target = candidates.find(node => {
      const label = clean((node.getAttribute("aria-label") || "") + " " +
        (node.innerText || node.textContent || ""));
      return /\breviews\b/i.test(label) && !/write a review|review this place/i.test(label);
    });
    if (!target) return false;
    try { target.click(); return true; } catch (_) { return false; }
  }

  async function runUnsortedAudit() {
    stopAuto("Preparing one-click audit…");
    const identity = identityCheck();
    if (!identity.ok) {
      verifiedIdentity = null;
      armed = false;
      status("AUDIT STOPPED — dealership identity did not pass. title:" +
        identity.titleOk + ", address:" + identity.addressOk +
        ", phone:" + identity.phoneOk + ". " +
        JSON.stringify(identity.diagnostic));
      return;
    }
    restoreVerifiedListing(identity);
    status("Dealership identity verified. Opening Google Reviews…");
    const alreadyHasCards = Boolean(document.querySelector("[data-review-id],.jftiEf"));
    if (!alreadyHasCards && !clickReviewsTab()) {
      status("Identity verified, but Google did not expose a Reviews tab to open. No collection started.");
      return;
    }
    let foundCards = false;
    for (let attempt = 0; attempt < 24; attempt++) {
      if (document.querySelector("[data-review-id],.jftiEf")) {
        foundCards = true;
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    if (!foundCards) {
      status("Identity verified, but no review cards appeared within 12 seconds. No collection started.");
      return;
    }
    armed = true;
    captureMode = "unfiltered-visible";
    sortVerificationMethod = null;
    status("Collecting all visible ratings without relying on the missing Lowest control. One-star records will be derived after capture.");
    captureVisible();
    autoCollect();
  }

  function autoCollect() {
    if (!armed) return status("Verify the dealership and arm a capture mode first.");
    if (autoTimer) return status("Auto-collect is already running.");
    const firstCard = document.querySelector("[data-review-id],.jftiEf");
    if (!firstCard) return status("No review cards found. Open the Reviews list first.");
    let feed = firstCard.parentElement;
    while (feed && feed !== document.body) {
      const css = getComputedStyle(feed);
      if (/(auto|scroll)/.test(css.overflowY) && feed.scrollHeight > feed.clientHeight + 30) break;
      feed = feed.parentElement;
    }
    if (!feed || feed === document.body) feed = document.querySelector('[role="feed"]');
    if (!feed) {
      const candidates = [...document.querySelectorAll("div")].filter(node => {
        if (!node.querySelector("[data-review-id],.jftiEf")) return false;
        const css = getComputedStyle(node);
        return /(auto|scroll)/.test(css.overflowY) &&
          node.scrollHeight > node.clientHeight + 30;
      });
      candidates.sort((a, b) =>
        (b.clientHeight * b.clientWidth) - (a.clientHeight * a.clientWidth));
      feed = candidates[0] || null;
    }
    if (!feed) return status("Could not identify the review feed. No data was changed.");
    autoIdle = 0;
    autoSteps = 0;
    autoStartedAt = new Date().toISOString();
    autoFinishedAt = null;
    autoStopReason = "running";
    autoBundleExported = false;
    status("AUTO-COLLECT running. Keep this tab open; do not navigate away.");
    autoTimer = setInterval(() => {
      if (!armed || !document.body.contains(feed)) return stopAuto("Stopped: review feed or capture state changed.");
      const beforeCount = cards.size;
      captureVisible();
      const added = cards.size - beforeCount;
      const beforeTop = feed.scrollTop;
      const maxTop = Math.max(0, feed.scrollHeight - feed.clientHeight);
      feed.scrollTop = Math.min(maxTop, beforeTop + Math.max(500, Math.floor(feed.clientHeight * 0.78)));
      feed.dispatchEvent(new Event("scroll", { bubbles: true }));
      autoSteps++;
      if (added > 0 || feed.scrollTop > beforeTop) autoIdle = 0;
      else autoIdle++;
      if (autoSteps >= 500) return stopAuto("Safety stop after 500 scroll cycles. " + cards.size + " reviews captured.");
      if (autoIdle >= 7 && feed.scrollTop >= maxTop - 5) {
        captureVisible();
        return stopAuto("Feed appears exhausted after 7 idle checks. " + cards.size + " unique reviews captured. Completeness is NOT verified.");
      }
      status("AUTO-COLLECT · " + cards.size + " unique · " +
        [...cards.values()].filter(x => x.rating_value === 1).length +
        " one-star · pass " + autoSteps);
    }, 1400);
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

  function exportAuditBundle() {
    persistCards();
    const rows = [...cards.values()];
    const oneStar = rows.filter(row => row.rating_value === 1);
    const bundle = {
      schema_version: "crmt-review-audit-bundle-1.0",
      generated_at_utc: new Date().toISOString(),
      listing: {
        title: verifiedIdentity?.title || "",
        url_at_verification: verifiedIdentity?.listing_url_at_verification || "",
        url_at_export: location.href,
        identity_checks: verifiedIdentity
      },
      collection: {
        collector: "crmt-android-userscript-0.5.0",
        mode: captureMode || "not-armed",
        sort_state: captureMode === "lowest" ? "lowest-confirmed" : "unverified-or-default-sort",
        sort_verification_method: sortVerificationMethod,
        started_at_utc: autoStartedAt,
        finished_at_utc: autoFinishedAt,
        stop_reason: autoStopReason,
        scroll_cycles: autoSteps,
        complete: false,
        completeness_note: "Visible Google Maps UI capture. Feed exhaustion and count matching do not prove complete historical coverage."
      },
      counts: {
        raw_unique_reviews: rows.length,
        one_star_reviews: oneStar.length,
        non_one_star_reviews: rows.filter(row => row.rating_value !== null && row.rating_value !== 1).length,
        unknown_rating_reviews: rows.filter(row => row.rating_value === null).length,
        missing_review_id: rows.filter(row => !row.review_id).length,
        missing_reviewer: rows.filter(row => !row.reviewer_name).length,
        missing_date: rows.filter(row => !row.published_at).length,
        missing_text: rows.filter(row => !row.review_text).length
      },
      raw_reviews: rows,
      one_star_reviews: oneStar
    };
    download("crmt-audit-bundle-" + Date.now() + ".json", JSON.stringify(bundle, null, 2), "application/json");
    autoBundleExported = true;
    status("AUTO-COLLECT finished. Evidence bundle downloaded: " + rows.length +
      " total reviews, " + oneStar.length + " one-star. Completeness remains unverified.");
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
    if (action === "run") {
      runUnsortedAudit();
    } else if (action === "hide") {
      panel.style.width = "42px";
      panel.style.height = "42px";
      panel.style.overflow = "hidden";
      panel.innerHTML = '<button data-action="show" style="width:32px;height:32px">CR</button>';
    } else if (action === "show") {
      location.reload();
    } else if (action === "configure") {
      const title = prompt("Exact dealership name:", EXPECTED.titleTokens.join(" "));
      if (title === null || !clean(title)) return;
      const address = prompt("Full dealership street address:", EXPECTED.address);
      if (address === null || !clean(address)) return;
      const phone = prompt("Dealership phone number:", EXPECTED.phone);
      if (phone === null || !clean(phone)) return;
      EXPECTED.titleTokens = norm(title).replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
      EXPECTED.address = clean(address);
      EXPECTED.phone = clean(phone);
      try { localStorage.setItem("crmt-review-config-v1", JSON.stringify(EXPECTED)); } catch (_) {}
      status("Configuration entered. Verify the dealership overview before collecting.");
    } else if (action === "identity") {
      const identity = identityCheck();
      armed = false;
      if (!identity.ok) {
        verifiedIdentity = null;
        status("IDENTITY FAIL — title:" + identity.titleOk +
          ", address:" + identity.addressOk + ", phone:" + identity.phoneOk +
          ". DIAGNOSTIC: " + JSON.stringify(identity.diagnostic) +
          ". Do not open Reviews yet.");
      } else {
        const nextStorageKey = "crmt-review-capture-" + hash(location.href.split("?")[0]).slice(6) + "-v1";
        if (nextStorageKey !== storageKey) {
          storageKey = nextStorageKey;
          restoreCards();
        }
        verifiedIdentity = {
          ...identity,
          verified_at_utc: new Date().toISOString(),
          listing_url_at_verification: location.href
        };
        status("Business identity verified on overview: " + identity.title +
          ". Restored " + cards.size + " saved review(s). Now open Reviews and choose Lowest.");
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
        captureMode = "lowest";
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
        captureMode = "lowest";
        status("Manually armed for " + verifiedIdentity.title +
          ". You confirmed Lowest is visibly selected. Capture and scroll carefully.");
        captureVisible();
      }
    } else if (action === "unsorted") {
      const hasReviewCards = document.querySelector("[data-review-id],.jftiEf");
      if (!verifiedIdentity || !hasReviewCards) {
        armed = false;
        status("Unsorted arm refused: verify the business overview first and open Reviews.");
      } else {
        armed = true;
        captureMode = "unfiltered-visible";
        sortVerificationMethod = null;
        status("Armed for " + verifiedIdentity.title +
          ". Capturing visible reviews without a verified sort. One-star rows will be filtered in export.");
        captureVisible();
      }
    } else if (action === "capture") captureVisible();
    else if (action === "auto") autoCollect();
    else if (action === "stop") stopAuto();
    else if (action === "scroll") scrollOnce();
    else if (action === "raw") { persistCards(); exportRaw(); }
    else if (action === "one") { persistCards(); exportOneStar(); }
    else if (action === "csv") { persistCards(); exportCsv(); }
    else if (action === "manifest") {
      persistCards();
      const rows = [...cards.values()];
      const identity = verifiedIdentity;
      download("crmt-greenville-manifest-" + Date.now() + ".json",
        JSON.stringify({
          created_at_utc: new Date().toISOString(),
          listing_title: identity?.title || "",
          listing_url_at_verification: identity?.listing_url_at_verification || "",
          listing_url_at_export: location.href,
          identity_checks: identity,
          lowest_selected_at_arm: captureMode === "lowest" && Boolean(sortVerificationMethod),
          lowest_verification_method: sortVerificationMethod,
          capture_mode: captureMode || "not-armed",
          sort_state: captureMode === "lowest" ? "lowest-confirmed" : captureMode === "unfiltered-visible" ? "unverified-or-default-sort" : "not-captured",
          raw_cards_captured: rows.length,
          auto_collection_started_at_utc: autoStartedAt,
          auto_collection_finished_at_utc: autoFinishedAt,
          auto_collection_stop_reason: autoStopReason,
          auto_collection_scroll_cycles: autoSteps,
          one_star_cards_captured: rows.filter(x => x.rating_value === 1).length,
          non_one_star_cards_captured: rows.filter(x => x.rating_value !== null && x.rating_value !== 1).length,
          unknown_rating_cards_captured: rows.filter(x => x.rating_value === null).length,
          cards_missing_review_id: rows.filter(x => !x.review_id).length,
          cards_missing_reviewer: rows.filter(x => !x.reviewer_name).length,
          cards_missing_date: rows.filter(x => !x.published_at).length,
          cards_missing_text: rows.filter(x => !x.review_text).length,
          last_capture_at_utc: lastCapture, complete: false,
          completeness_note: "User-controlled visible-card capture. No claim of complete historical coverage."
        }, null, 2), "application/json");
    }
  });

  observer = new MutationObserver(records => {
    if (armed && records.some(record => !panel.contains(record.target))) captureVisible();
  });
  observer.observe(document.body, { childList: true, subtree: true });
  restoreCards();
  status("Pilot 0.5.0 loaded. Waiting for the verified Greenville business profile.");

  // Start automatically only when the selected page title itself identifies
  // the expected dealership and the address + phone checks also pass.
  let autoLaunchAttempts = 0;
  let autoLaunchTimer = setInterval(() => {
    autoLaunchAttempts++;
    const identity = identityCheck();
    if (identity.ok) {
      clearInterval(autoLaunchTimer);
      autoLaunchTimer = null;
      status("Verified Greenville profile detected. Starting automatic audit…");
      runUnsortedAudit();
    } else if (autoLaunchAttempts >= 45) {
      clearInterval(autoLaunchTimer);
      autoLaunchTimer = null;
      status("Automatic start not triggered. Open the verified Greenville business overview, or use RUN AUDIT.");
    }
  }, 1000);
})();
