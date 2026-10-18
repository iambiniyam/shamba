const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const selected = document.getElementById("selected");
const preview = document.getElementById("preview");
const go = document.getElementById("go");
const reset = document.getElementById("reset");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const verdict = document.getElementById("verdict");
const timing = document.getElementById("timing");
const resultTitle = document.getElementById("result-title");
const confidence = document.getElementById("confidence");
const confidenceNote = document.getElementById("confidence-note");
const alternatives = document.getElementById("alternatives");
const summary = document.getElementById("summary");
const adviceSections = document.getElementById("advice-sections");
const escalate = document.getElementById("escalate");
const disclaimer = document.getElementById("disclaimer");
const historySection = document.getElementById("history");
const historyStatus = document.getElementById("history-status");
const historyList = document.getElementById("history-list");
const clearHistoryButton = document.getElementById("clear-history");

const MAX_BYTES = 12 * 1024 * 1024;
const state = { file: null, url: null };
const timestampFormat = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function percent(value) {
  const number = Number(value) * 100;
  if (number >= 99.95) return "99.9%+";
  if (number < 0.1) return "<0.1%";
  return `${number.toFixed(1)}%`;
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function clearPreview() {
  if (state.url) URL.revokeObjectURL(state.url);
  state.url = null;
  preview.hidden = true;
  preview.removeAttribute("src");
}

function setFile(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    setStatus("Choose a JPG or PNG image.", true);
    return;
  }
  if (file.size > MAX_BYTES) {
    setStatus("That image is larger than 12 MB. Choose a smaller photo.", true);
    return;
  }
  state.file = file;
  selected.hidden = false;
  selected.textContent = file.name;
  clearPreview();
  state.url = URL.createObjectURL(file);
  preview.src = state.url;
  preview.hidden = false;
  reset.hidden = false;
  result.hidden = true;
  setStatus("");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.add("is-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.remove("is-over");
  });
});

drop.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (file) setFile(file);
});

document.addEventListener("paste", (event) => {
  const items = event.clipboardData ? event.clipboardData.items : [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        setFile(file);
        setStatus("Image pasted. Click Diagnose leaf.");
      }
      break;
    }
  }
});

function adviceSection(title, items) {
  if (!items || !items.length) return "";
  return `<section class="card"><h3>${escapeHtml(title)}</h3><ul>${items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("")}</ul></section>`;
}

function render(data) {
  const top = data.predictions[0];
  const advice = data.advice;
  const low = Number(top.confidence) < 0.6;

  result.hidden = false;
  timing.textContent = `${data.took_ms} ms`;
  verdict.textContent = advice.healthy ? "Likely healthy" : low ? "Uncertain" : "Possible disease";
  verdict.classList.toggle("is-warn", !advice.healthy);
  resultTitle.textContent = `${advice.crop} · ${advice.disease}`;
  confidence.textContent = `${percent(top.confidence)} confidence`;
  confidenceNote.innerHTML = advice.confidence_note
    ? `<div class="note-box">${escapeHtml(advice.confidence_note)}</div>`
    : "";

  const others = data.predictions.slice(1);
  alternatives.innerHTML = others.length
    ? others.map((prediction) => {
      const width = Math.max(4, Math.round((Number(prediction.confidence) / top.confidence) * 100));
      return `<li>
        <span>${escapeHtml(prediction.crop)} · ${escapeHtml(prediction.disease)}</span>
        <span>${percent(prediction.confidence)}</span>
        <span class="bar"><span style="width:${width}%"></span></span>
      </li>`;
      }).join("")
    : '<li><span>No close alternatives in the supported classes.</span></li>';

  summary.textContent = advice.summary;
  adviceSections.innerHTML = [
    adviceSection("Do now", advice.act_now),
    adviceSection("Low-cost and organic", advice.organic),
    adviceSection("Chemical, only if needed", advice.chemical),
    adviceSection("Prevent next season", advice.prevent),
  ].join("");

  escalate.innerHTML = advice.escalate
    ? `<div class="escalate"><h3>When to escalate</h3><p>${escapeHtml(advice.escalate)}</p></div>`
    : "";
  disclaimer.textContent = advice.disclaimer;
  resultTitle.focus();
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown time";
  return timestampFormat.format(date);
}

function renderHistory(entries) {
  const items = Array.isArray(entries) ? entries : [];
  if (!items.length) {
    historyList.innerHTML = "";
    historyList.hidden = true;
    historyStatus.hidden = false;
    historyStatus.classList.remove("is-error");
    historyStatus.textContent = "No diagnoses yet. Your saved results will appear here.";
    clearHistoryButton.hidden = true;
    return;
  }

  historyStatus.hidden = true;
  historyStatus.classList.remove("is-error");
  historyList.innerHTML = items
    .map((entry) => {
      const healthy = Boolean(entry.healthy);
      const crop = escapeHtml(entry.crop || "Unknown crop");
      const disease = escapeHtml(entry.disease || "Unknown result");
      const source = escapeHtml(entry.source || "unknown file");
      const when = escapeHtml(formatTimestamp(entry.timestamp));
      const stamp = escapeHtml(entry.timestamp);
      return `<li class="history-row">
        <span class="history-dot${healthy ? " is-healthy" : ""}" aria-hidden="true"></span>
        <div class="history-detail">
          <p class="history-crop">${crop} <span class="history-disease">· ${disease}</span></p>
          <p class="history-meta"><time datetime="${stamp}">${when}</time> · <span class="history-source">${source}</span></p>
        </div>
        <span class="history-confidence">${percent(entry.confidence)}</span>
      </li>`;
    })
    .join("");
  historyList.hidden = false;
  clearHistoryButton.hidden = false;
}

async function loadHistory() {
  historySection.setAttribute("aria-busy", "true");
  clearHistoryButton.disabled = true;
  clearHistoryButton.hidden = true;
  historyList.hidden = true;
  historyStatus.hidden = false;
  historyStatus.classList.remove("is-error");
  historyStatus.textContent = "Loading recent diagnoses…";

  try {
    const response = await fetch("/api/history", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    const data = await response.json();
    renderHistory(data.entries);
  } catch (error) {
    historyList.innerHTML = "";
    historyList.hidden = true;
    historyStatus.hidden = false;
    historyStatus.textContent = "History is unavailable right now.";
    historyStatus.classList.add("is-error");
  } finally {
    clearHistoryButton.disabled = false;
    historySection.setAttribute("aria-busy", "false");
  }
}

async function clearHistory() {
  if (!window.confirm("Clear all saved diagnoses from this device?")) return;
  historySection.setAttribute("aria-busy", "true");
  clearHistoryButton.disabled = true;
  clearHistoryButton.textContent = "Clearing…";

  try {
    const response = await fetch("/api/history", { method: "DELETE" });
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    renderHistory([]);
    historyStatus.textContent = "History cleared. New diagnoses will appear here.";
  } catch (error) {
    historyStatus.hidden = false;
    historyStatus.textContent = "Could not clear history. Try again.";
    historyStatus.classList.add("is-error");
  } finally {
    clearHistoryButton.textContent = "Clear history";
    clearHistoryButton.disabled = false;
    historySection.setAttribute("aria-busy", "false");
  }
}

async function diagnose() {
  if (!state.file) {
    setStatus("Choose or take a leaf photo first.", true);
    return;
  }
  go.disabled = true;
  go.textContent = "Reading the leaf...";
  setStatus("Running the local model.");
  result.hidden = true;
  document.querySelector("main").setAttribute("aria-busy", "true");

  const body = new FormData();
  body.append("file", state.file);
  body.append("top_k", "3");

  try {
    const response = await fetch("/api/diagnose", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    render(data);
    setStatus("Done. Check the confidence before acting.");
    loadHistory();
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    go.disabled = false;
    go.textContent = "Diagnose leaf";
    document.querySelector("main").setAttribute("aria-busy", "false");
  }
}

go.addEventListener("click", diagnose);

reset.addEventListener("click", () => {
  state.file = null;
  fileInput.value = "";
  selected.hidden = true;
  clearPreview();
  reset.hidden = true;
  result.hidden = true;
  setStatus("");
  fileInput.focus();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    diagnose();
  }
});

clearHistoryButton.addEventListener("click", clearHistory);
loadHistory();
