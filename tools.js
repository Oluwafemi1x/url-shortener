"use strict";

const API_BASE = "https://pyc0.onrender.com";
const SHORT_HOST = "pyc0.onrender.com";

function normalizeWebUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) throw new Error("Enter a URL.");
  const candidate = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(raw) ? raw : "https://" + raw;
  const parsed = new URL(candidate);
  if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Only http:// and https:// URLs are supported.");
  return parsed.href;
}

function pycoderCode(value) {
  const parsed = new URL(String(value || "").trim());
  if (parsed.hostname !== SHORT_HOST) throw new Error("Enter a pyc0.onrender.com short link.");
  const code = parsed.pathname.replace(/^\/+|\/+$/g, "");
  if (!/^[A-Za-z0-9_-]{5,30}$/.test(code)) throw new Error("Enter a valid Pycoder short link.");
  return code;
}

async function jsonRequest(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) throw new Error(payload?.error || "Request failed. Please try again.");
    return { response, payload };
  } catch (error) {
    if (error?.name === "AbortError") throw new Error("The service took too long to respond. Please try again.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function setMessage(element, text, isError = false) {
  if (!element) return;
  element.textContent = text || "";
  element.hidden = !text;
  element.className = isError ? "message error" : "message";
}

async function copyText(text, button) {
  await navigator.clipboard.writeText(text);
  const old = button.textContent;
  button.textContent = "Copied!";
  setTimeout(() => button.textContent = old, 1200);
}

function prefill(id) {
  const value = new URLSearchParams(location.search).get("url");
  const input = document.getElementById(id);
  if (value && input) input.value = value;
  return Boolean(value);
}

async function setupQr() {
  const form = document.getElementById("qrForm");
  if (!form) return;
  const input = document.getElementById("qrUrl");
  const error = document.getElementById("toolError");
  const result = document.getElementById("qrResult");
  const image = document.getElementById("qrImage");
  const download = document.getElementById("qrDownload");
  let objectUrl = null;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(error, "");
    try {
      const url = normalizeWebUrl(input.value);
      const response = await fetch(API_BASE + "/api/qr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Could not generate the QR code.");
      }
      const blob = await response.blob();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(blob);
      image.src = objectUrl;
      download.href = objectUrl;
      download.download = "pycoder-qr.png";
      result.hidden = false;
    } catch (err) {
      setMessage(error, err.message, true);
    }
  });

  if (prefill("qrUrl")) form.requestSubmit();
}

function setupUtm() {
  const form = document.getElementById("utmForm");
  if (!form) return;
  const output = document.getElementById("utmOutput");
  const result = document.getElementById("utmResult");
  const error = document.getElementById("toolError");
  const copy = document.getElementById("copyUtm");
  const shorten = document.getElementById("shortenUtm");
  const shortOutput = document.getElementById("shortUtmOutput");

  function build() {
    const url = new URL(normalizeWebUrl(document.getElementById("utmUrl").value));
    const fields = [
      ["utm_source", "utmSource"],
      ["utm_medium", "utmMedium"],
      ["utm_campaign", "utmCampaign"],
      ["utm_term", "utmTerm"],
      ["utm_content", "utmContent"]
    ];
    for (const [param, id] of fields) {
      const value = document.getElementById(id).value.trim();
      if (value) url.searchParams.set(param, value);
      else url.searchParams.delete(param);
    }
    return url.href;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    setMessage(error, "");
    try {
      const url = build();
      output.textContent = url;
      output.href = url;
      shortOutput.textContent = "";
      result.hidden = false;
    } catch (err) {
      setMessage(error, err.message, true);
    }
  });

  copy.addEventListener("click", () => copyText(output.href, copy));
  shorten.addEventListener("click", async () => {
    setMessage(error, "");
    try {
      const url = output.href || build();
      const { payload } = await jsonRequest(API_BASE + "/api/shorten", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      shortOutput.textContent = payload.short_url;
      result.hidden = false;
    } catch (err) {
      setMessage(error, err.message, true);
    }
  });
}

async function setupExpander() {
  const form = document.getElementById("expandForm");
  if (!form) return;
  const input = document.getElementById("expandUrl");
  const result = document.getElementById("expandResult");
  const error = document.getElementById("toolError");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(error, "");
    try {
      const { payload } = await jsonRequest(API_BASE + "/api/expand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ short_url: input.value.trim() })
      });
      document.getElementById("expandDestination").textContent = payload.original_url;
      document.getElementById("expandDestination").href = payload.original_url;
      document.getElementById("expandClicks").textContent = String(payload.clicks);
      document.getElementById("expandCreated").textContent = new Date(payload.created_at).toLocaleString();
      result.hidden = false;
    } catch (err) {
      setMessage(error, err.message, true);
    }
  });

  if (prefill("expandUrl")) form.requestSubmit();
}

function renderRows(container, rows, emptyText) {
  container.replaceChildren();
  if (!rows?.length) {
    const row = document.createElement("div");
    row.className = "breakdown-row";
    row.textContent = emptyText;
    container.appendChild(row);
    return;
  }
  for (const item of rows) {
    const row = document.createElement("div");
    row.className = "breakdown-row";
    const name = document.createElement("span");
    name.textContent = item.name;
    const count = document.createElement("strong");
    count.textContent = String(item.count);
    row.append(name, count);
    container.appendChild(row);
  }
}

async function setupTracker() {
  const form = document.getElementById("trackerForm");
  if (!form) return;
  const input = document.getElementById("trackerUrl");
  const error = document.getElementById("toolError");
  const result = document.getElementById("trackerResult");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage(error, "");
    try {
      const code = pycoderCode(input.value);
      const { payload } = await jsonRequest(API_BASE + "/api/analytics/" + encodeURIComponent(code));
      document.getElementById("metricClicks").textContent = String(payload.link.clicks);
      document.getElementById("metricCode").textContent = payload.link.code;
      document.getElementById("metricCreated").textContent = new Date(payload.link.created_at).toLocaleDateString();
      const original = document.getElementById("trackerDestination");
      original.textContent = payload.link.original_url;
      original.href = payload.link.original_url;

      const chart = document.getElementById("dailyChart");
      chart.replaceChildren();
      const max = Math.max(1, ...payload.daily.map(item => item.count));
      for (const item of payload.daily) {
        const bar = document.createElement("div");
        bar.className = "chart-bar";
        bar.style.height = Math.max(2, Math.round((item.count / max) * 100)) + "%";
        bar.title = item.date + ": " + item.count + " clicks";
        chart.appendChild(bar);
      }

      renderRows(document.getElementById("deviceRows"), payload.devices, "No device data yet.");
      renderRows(document.getElementById("referrerRows"), payload.referrers, "No referrer data yet.");
      result.hidden = false;
    } catch (err) {
      setMessage(error, err.message, true);
    }
  });

  if (prefill("trackerUrl")) form.requestSubmit();
}

document.addEventListener("DOMContentLoaded", () => {
  setupQr();
  setupUtm();
  setupExpander();
  setupTracker();
});
