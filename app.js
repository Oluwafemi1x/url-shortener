"use strict";

const API_ENDPOINT = "https://is.gd/create.php";
const HISTORY_KEY = "pycoder-url-shortener-history-v2";
const MAX_HISTORY = 20;

const form = document.getElementById("shortenForm");
const longUrlInput = document.getElementById("longUrl");
const customAliasInput = document.getElementById("customAlias");
const logStatsInput = document.getElementById("logStats");
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

function normalizeUrl(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) {
    throw new Error("Enter a URL to shorten.");
  }

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

  if (!/^[A-Za-z0-9_]{5,30}$/.test(alias)) {
    throw new Error("Custom aliases must be 5–30 letters, numbers or underscores.");
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

function shortenWithJsonp(url, alias, logStats) {
  return new Promise((resolve, reject) => {
    const callbackName = "pycoderShortener_" + Date.now() + "_" + Math.random().toString(36).slice(2);
    const params = new URLSearchParams({
      format: "json",
      url,
      callback: callbackName
    });

    if (alias) params.set("shorturl", alias);
    if (logStats) params.set("logstats", "1");

    const script = document.createElement("script");
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error("The shortening service took too long to respond. Please try again."));
    }, 12000);

    function cleanup() {
      window.clearTimeout(timeout);
      script.remove();
      try {
        delete window[callbackName];
      } catch {
        window[callbackName] = undefined;
      }
    }

    window[callbackName] = (payload) => {
      cleanup();

      if (!payload || payload.errorcode || payload.errormessage) {
        reject(new Error(payload?.errormessage || "The shortening service returned an error."));
        return;
      }

      if (!payload.shorturl || !/^https:\/\/is\.gd\/[A-Za-z0-9_]+$/.test(payload.shorturl)) {
        reject(new Error("The shortening service returned an unexpected response."));
        return;
      }

      resolve(payload.shorturl);
    };

    script.onerror = () => {
      cleanup();
      reject(new Error("Unable to reach the shortening service. Check your connection and try again."));
    };

    script.referrerPolicy = "no-referrer";
    script.src = API_ENDPOINT + "?" + params.toString();
    document.head.appendChild(script);
  });
}

function getHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(value) ? value.filter(isHistoryItem).slice(0, MAX_HISTORY) : [];
  } catch {
    return [];
  }
}

function isHistoryItem(item) {
  return item &&
    typeof item.originalUrl === "string" &&
    typeof item.shortUrl === "string" &&
    /^https:\/\/is\.gd\/[A-Za-z0-9_]+$/.test(item.shortUrl);
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
  setTimeout(() => {
    button.textContent = previous;
  }, 1400);
}

function showResult(entry) {
  latestResult = entry;
  resultOriginal.textContent = entry.originalUrl;
  shortUrlAnchor.textContent = entry.shortUrl;
  shortUrlAnchor.href = entry.shortUrl;
  openButton.href = entry.shortUrl;

  if (entry.logStats) {
    statsButton.href = entry.shortUrl + "-";
    statsButton.hidden = false;
  } else {
    statsButton.hidden = true;
    statsButton.removeAttribute("href");
  }

  resultPanel.hidden = false;
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

  if (entry.logStats) {
    const stats = document.createElement("a");
    stats.href = entry.shortUrl + "-";
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
    const shortUrl = await shortenWithJsonp(originalUrl, alias, logStatsInput.checked);

    const entry = {
      originalUrl,
      shortUrl,
      logStats: logStatsInput.checked,
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
      if (error?.name === "AbortError") return;
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
