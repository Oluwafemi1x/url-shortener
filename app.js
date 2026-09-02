"use strict";

const PRIMARY_API = "https://spoo.me/";
const FALLBACK_API = "https://cleanuri.com/api/v1/shorten";
const HISTORY_KEY = "pycoder-url-shortener-history-v3";
const MAX_HISTORY = 20;
const REQUEST_TIMEOUT_MS = 10000;

const form = document.getElementById("shortenForm");
const longUrlInput = document.getElementById("longUrl");
const customAliasInput = document.getElementById("customAlias");
const formError = document.getElementById("formError");
const shortenButton = document.getElementById("shortenButton");
const buttonLabel = shortenButton.querySelector(".button-label");
const spinner = shortenButton.querySelector(".spinner");

const resultPanel = document.getElementById("resultPanel");
const resultOriginal = document.getElementById("resultOriginal");
const shortUrlAnchor = document.getElementById("shortUrl");
const copyButton = document.getElementById("copyButton");
const shareButton = document.getElementById("shareButton");
const openButton = document.getElementById("openButton");
const statsButton = document.getElementById("statsButton");

const historyList = document.getElementById("historyList");
const emptyHistory = document.getElementById("emptyHistory");
const clearHistoryButton = document.getElementById("clearHistoryButton");

let latestResult = null;

class ProviderError extends Error {
  constructor(message, retryable = false) {
    super(message);
    this.name = "ProviderError";
    this.retryable = retryable;
  }
}

function normalizeUrl(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) throw new Error("Enter a URL to shorten.");

  const candidate = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(trimmed)
    ? trimmed
    : "https://" + trimmed;

  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("Enter a valid web address.");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("Only http:// and https:// URLs are supported.");
  }

  if (!parsed.hostname || parsed.hostname.length < 3) {
    throw new Error("Enter a valid web address with a hostname.");
  }

  if (parsed.href.length > 5000) {
    throw new Error("The URL is too long. Maximum length is 5,000 characters.");
  }

  return parsed.href;
}

function validateAlias(value) {
  const alias = String(value || "").trim();
  if (!alias) return "";

  if (!/^[A-Za-z0-9]{1,15}$/.test(alias)) {
    throw new Error("Custom aliases can contain only letters and numbers, up to 15 characters.");
  }

  return alias;
}

function setLoading(isLoading) {
  shortenButton.disabled = isLoading;
  spinner.hidden = !isLoading;
  buttonLabel.textContent = isLoading ? "Creating short link…" : "Shorten URL";
}

function showError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearError() {
  formError.textContent = "";
  formError.hidden = true;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new ProviderError("The shortening provider did not respond in time.", true);
    }
    throw new ProviderError("Unable to reach the shortening provider. Check your connection and try again.", true);
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function readJsonSafely(response) {
  const text = await response.text();
  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    throw new ProviderError("The shortening provider returned an unexpected response.", response.status >= 500);
  }
}

async function shortenWithSpoo(originalUrl, alias) {
  const body = new URLSearchParams({ url: originalUrl });
  if (alias) body.set("alias", alias);

  const response = await fetchWithTimeout(PRIMARY_API, {
    method: "POST",
    mode: "cors",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    },
    body
  });

  const payload = await readJsonSafely(response);

  if (!response.ok) {
    const message =
      payload.message ||
      payload.error ||
      payload.detail ||
      "The shortening provider could not create this link.";

    const retryable = response.status === 429 || response.status >= 500;
    throw new ProviderError(String(message), retryable);
  }

  const shortUrl = payload.short_url;
  if (typeof shortUrl !== "string" || !/^https:\/\/spoo\.me\/[A-Za-z0-9_-]+$/.test(shortUrl)) {
    throw new ProviderError("The shortening provider returned an invalid short URL.", true);
  }

  return { shortUrl, provider: "spoo" };
}

async function shortenWithCleanUri(originalUrl) {
  const body = new URLSearchParams({ url: originalUrl });

  const response = await fetchWithTimeout(FALLBACK_API, {
    method: "POST",
    mode: "cors",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    },
    body
  }, 8000);

  const payload = await readJsonSafely(response);

  if (!response.ok || payload.error) {
    throw new ProviderError(
      String(payload.error || "The backup shortening provider could not create this link."),
      response.status === 429 || response.status >= 500
    );
  }

  const shortUrl = payload.result_url;
  if (typeof shortUrl !== "string" || !/^https:\/\/cleanuri\.com\/[A-Za-z0-9_-]+$/.test(shortUrl)) {
    throw new ProviderError("The backup provider returned an invalid short URL.");
  }

  return { shortUrl, provider: "cleanuri" };
}

async function createShortLink(originalUrl, alias) {
  try {
    return await shortenWithSpoo(originalUrl, alias);
  } catch (primaryError) {
    if (alias || !(primaryError instanceof ProviderError) || !primaryError.retryable) {
      throw primaryError;
    }

    try {
      return await shortenWithCleanUri(originalUrl);
    } catch {
      throw new Error("The shortening services are temporarily unreachable from your browser. Please try again shortly.");
    }
  }
}

function getHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(value) ? value.filter(isHistoryItem).slice(0, MAX_HISTORY) : [];
  } catch {
    return [];
  }
}

function isSupportedShortUrl(value) {
  return /^https:\/\/(spoo\.me|cleanuri\.com|is\.gd)\/[A-Za-z0-9_-]+$/.test(value);
}

function isHistoryItem(item) {
  return item &&
    typeof item.originalUrl === "string" &&
    typeof item.shortUrl === "string" &&
    isSupportedShortUrl(item.shortUrl);
}

function saveHistory(entry) {
  const history = getHistory().filter((item) => item.shortUrl !== entry.shortUrl);
  history.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  renderHistory();
}

function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
}

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  const previous = button.textContent;
  button.textContent = "Copied!";
  window.setTimeout(() => {
    button.textContent = previous;
  }, 1400);
}

function statsUrlFor(entry) {
  if (entry.provider !== "spoo") return null;

  try {
    const code = new URL(entry.shortUrl).pathname.replace(/^\/+/, "");
    return code ? "https://spoo.me/stats/" + encodeURIComponent(code) : null;
  } catch {
    return null;
  }
}

function showResult(entry) {
  latestResult = entry;
  resultOriginal.textContent = entry.originalUrl;
  shortUrlAnchor.textContent = entry.shortUrl;
  shortUrlAnchor.href = entry.shortUrl;
  openButton.href = entry.shortUrl;

  const statsUrl = statsUrlFor(entry);
  if (statsUrl) {
    statsButton.href = statsUrl;
    statsButton.hidden = false;
  } else {
    statsButton.hidden = true;
    statsButton.removeAttribute("href");
  }

  resultPanel.hidden = false;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function createHistoryItem(entry) {
  const article = document.createElement("article");
  article.className = "history-item";

  const links = document.createElement("div");
  links.className = "history-links";

  const shortLink = document.createElement("a");
  shortLink.href = entry.shortUrl;
  shortLink.target = "_blank";
  shortLink.rel = "noreferrer";
  shortLink.textContent = entry.shortUrl;

  const original = document.createElement("span");
  original.textContent = entry.originalUrl;

  links.append(shortLink, original);

  const actions = document.createElement("div");
  actions.className = "history-actions";

  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "Copy";
  copy.addEventListener("click", () => copyText(entry.shortUrl, copy));

  const open = document.createElement("a");
  open.href = entry.shortUrl;
  open.target = "_blank";
  open.rel = "noreferrer";
  open.textContent = "Open ↗";

  actions.append(copy, open);

  const statsUrl = statsUrlFor(entry);
  if (statsUrl) {
    const stats = document.createElement("a");
    stats.href = statsUrl;
    stats.target = "_blank";
    stats.rel = "noreferrer";
    stats.textContent = "Stats ↗";
    actions.append(stats);
  }

  article.append(links, actions);
  return article;
}

function renderHistory() {
  const history = getHistory();
  historyList.replaceChildren();

  for (const entry of history) {
    historyList.appendChild(createHistoryItem(entry));
  }

  const hasHistory = history.length > 0;
  emptyHistory.hidden = hasHistory;
  clearHistoryButton.hidden = !hasHistory;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  let originalUrl;
  let alias;

  try {
    originalUrl = normalizeUrl(longUrlInput.value);
    alias = validateAlias(customAliasInput.value);
  } catch (error) {
    showError(error.message);
    return;
  }

  setLoading(true);

  try {
    const result = await createShortLink(originalUrl, alias);
    const entry = {
      originalUrl,
      shortUrl: result.shortUrl,
      provider: result.provider,
      createdAt: new Date().toISOString()
    };

    showResult(entry);
    saveHistory(entry);
  } catch (error) {
    showError(error instanceof Error ? error.message : "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});

copyButton.addEventListener("click", () => {
  if (latestResult) copyText(latestResult.shortUrl, copyButton);
});

shareButton.addEventListener("click", async () => {
  if (!latestResult) return;

  if (navigator.share) {
    try {
      await navigator.share({
        title: "Short link",
        text: "Here is the shortened link:",
        url: latestResult.shortUrl
      });
      return;
    } catch (error) {
      if (error && error.name === "AbortError") return;
    }
  }

  await copyText(latestResult.shortUrl, shareButton);
});

clearHistoryButton.addEventListener("click", () => {
  if (window.confirm("Clear your locally saved short-link history?")) {
    clearHistory();
  }
});

renderHistory();
