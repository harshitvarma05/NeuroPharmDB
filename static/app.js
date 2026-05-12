const state = {
  rows: [],
  activeBrowseId: null,
  searchTimers: {},
  nextRowId: 1,
  textStore: {},
  nextTextId: 1,
};

const els = {
  drugCount: document.querySelector("#drugCount"),
  interactionCount: document.querySelector("#interactionCount"),
  themeToggle: document.querySelector("#themeToggle"),
  drugRows: document.querySelector("#drugRows"),
  addDrugButton: document.querySelector("#addDrugButton"),
  checkButton: document.querySelector("#checkButton"),
  selectionHint: document.querySelector("#selectionHint"),
  resultPanel: document.querySelector("#resultPanel"),
  detailsGrid: document.querySelector("#detailsGrid"),
  browseTabs: document.querySelector("#browseTabs"),
  browseFilter: document.querySelector("#browseFilter"),
  interactionList: document.querySelector("#interactionList"),
};

const fmt = new Intl.NumberFormat();

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pillClass(severity) {
  return `severity ${severity || "informational"}`;
}

function plainPreview(text, limit) {
  const clean = String(text || "").trim();
  if (clean.length <= limit) return clean;
  const sliced = clean.slice(0, limit).replace(/\s+\S*$/, "").trim();
  return `${sliced}...`;
}

function textToBullets(text, maxItems = 5) {
  const clean = String(text || "").trim();
  if (!clean) return [];

  let parts = clean
    .replace(/\s+(\d+\))/g, "\n$1")
    .split(/\n+|(?<=[.!?])\s+(?=[A-Z0-9])/)
    .map((part) => part.replace(/^\d+\)\s*/, "").trim())
    .filter(Boolean);

  if (parts.length <= 1) {
    parts = clean
      .split(/;\s+|,\s+(?=(?:and|while|with|which|then)\b)/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  return parts.slice(0, maxItems);
}

function bulletList(items, options = {}) {
  if (!items.length) return "";
  const hasMore = Boolean(options.textId);
  const lastIndex = items.length - 1;
  return `
    <ul class="bullet-list">
      ${items
        .map((item, index) => {
          const readMore =
            hasMore && index === lastIndex
              ? ` <button class="read-more-inline" type="button" data-action="read-more">Read more</button>`
              : "";
          return `<li>${escapeHtml(item)}${readMore}</li>`;
        })
        .join("")}
    </ul>
  `;
}

function expandableText(title, text, limit = 520, maxItems = 4) {
  const clean = String(text || "").trim();
  if (!clean) return "";
  const preview = plainPreview(clean, limit);
  const previewItems = textToBullets(preview, maxItems);
  if (clean.length <= limit) return bulletList(previewItems);

  const id = `txt-${state.nextTextId++}`;
  state.textStore[id] = { title, text: clean };
  return `
    <div class="readmore-block" data-text-id="${id}">
      ${bulletList(previewItems, { textId: id })}
    </div>
  `;
}

function showReaderModal(item) {
  document.querySelector(".reader-modal")?.remove();
  const modal = document.createElement("div");
  modal.className = "reader-modal";
  modal.innerHTML = `
    <div class="reader-backdrop" data-action="close-reader"></div>
    <section class="reader-panel glass" role="dialog" aria-modal="true" aria-label="${escapeHtml(item.title)}">
      <div class="reader-head">
        <h2>${escapeHtml(item.title)}</h2>
        <button class="icon-button" type="button" data-action="close-reader" aria-label="Close reader">×</button>
      </div>
      ${bulletList(textToBullets(item.text, 80))}
    </section>
  `;
  document.body.appendChild(modal);
}

async function api(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

async function loadStats() {
  const stats = await api("/api/stats");
  els.drugCount.textContent = fmt.format(stats.drugs);
  els.interactionCount.textContent = fmt.format(stats.interactions);
}

function selectedRows() {
  return state.rows.filter((row) => row.drug);
}

function addDrugRow(drug = null) {
  const row = { rowId: state.nextRowId++, drug, detail: null };
  state.rows.push(row);
  renderDrugRows();
  updateSelectedState();
  return row;
}

function removeDrugRow(rowId) {
  if (state.rows.length <= 2) {
    clearDrug(rowId);
    return;
  }
  state.rows = state.rows.filter((row) => row.rowId !== rowId);
  if (!selectedRows().some((row) => row.drug?.id === state.activeBrowseId)) {
    state.activeBrowseId = selectedRows()[0]?.drug?.id || null;
  }
  renderDrugRows();
  updateSelectedState();
  renderDetails();
  renderBrowseTabs();
  loadInteractionList();
}

function renderDrugRows() {
  els.drugRows.innerHTML = state.rows
    .map((row, index) => `
      <div class="drug-picker" data-row-id="${row.rowId}">
        <label for="drug-${row.rowId}">Drug ${index + 1}</label>
        <div class="input-wrap">
          <input id="drug-${row.rowId}" type="search" autocomplete="off" placeholder="Search or open dropdown" value="${escapeHtml(row.drug?.name || "")}">
          <button type="button" class="dropdown-button" data-action="dropdown" title="Show drug options" aria-label="Show drug ${index + 1} options"></button>
          <button type="button" class="clear-button" data-action="clear" title="Clear drug">×</button>
          <button type="button" class="remove-button" data-action="remove" title="Remove drug" aria-label="Remove drug ${index + 1}">−</button>
        </div>
        <div class="suggestions" role="listbox"></div>
      </div>
    `)
    .join("");

  els.drugRows.querySelectorAll(".drug-picker").forEach((picker) => {
    const rowId = Number(picker.dataset.rowId);
    const input = picker.querySelector("input");
    const dropdownButton = picker.querySelector('[data-action="dropdown"]');
    const clearButton = picker.querySelector('[data-action="clear"]');
    const removeButton = picker.querySelector('[data-action="remove"]');

    input.addEventListener("input", () => {
      const row = getRow(rowId);
      row.drug = null;
      row.detail = null;
      const q = input.value.trim();
      clearSuggestions(picker);
      window.clearTimeout(state.searchTimers[rowId]);
      updateSelectedState();
      if (q.length < 2) return;
      state.searchTimers[rowId] = window.setTimeout(() => searchDrugs(rowId, q), 160);
    });

    input.addEventListener("focus", () => {
      const suggestions = picker.querySelector(".suggestions");
      if (suggestions.innerHTML) suggestions.classList.add("open");
    });

    dropdownButton.addEventListener("click", () => openDrugOptions(rowId));
    clearButton.addEventListener("click", () => clearDrug(rowId));
    removeButton.addEventListener("click", () => removeDrugRow(rowId));
  });
}

function getRow(rowId) {
  return state.rows.find((row) => row.rowId === rowId);
}

function getPicker(rowId) {
  return els.drugRows.querySelector(`.drug-picker[data-row-id="${rowId}"]`);
}

function clearSuggestions(picker) {
  const suggestions = picker.querySelector(".suggestions");
  suggestions.classList.remove("open");
  suggestions.innerHTML = "";
  suggestions.dataset.mode = "";
}

async function searchDrugs(rowId, q) {
  const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
  renderSuggestions(rowId, data.results, "Try another spelling or synonym.", "search");
}

async function openDrugOptions(rowId) {
  const picker = getPicker(rowId);
  const input = picker.querySelector("input");
  const suggestions = picker.querySelector(".suggestions");

  if (suggestions.classList.contains("open") && suggestions.dataset.mode === "dropdown") {
    suggestions.classList.remove("open");
    return;
  }

  suggestions.dataset.mode = "dropdown";
  suggestions.innerHTML = `<div class="suggestion static"><strong>Loading drugs</strong><small>Showing real database results...</small></div>`;
  suggestions.classList.add("open");

  const q = input.value.trim();
  const endpoint = q.length >= 2 ? `/api/options?q=${encodeURIComponent(q)}` : "/api/options";
  const data = await api(endpoint);
  renderSuggestions(
    rowId,
    data.results,
    q ? "No matches for this field." : "Type in the field to search all 19k drugs.",
    "dropdown",
  );
}

function renderSuggestions(rowId, results, emptyText, mode) {
  const picker = getPicker(rowId);
  const suggestions = picker.querySelector(".suggestions");
  suggestions.dataset.mode = mode;

  if (!results.length) {
    suggestions.innerHTML = `<div class="suggestion static"><strong>No matches</strong><small>${escapeHtml(emptyText)}</small></div>`;
    suggestions.classList.add("open");
    return;
  }

  const helper =
    mode === "dropdown"
      ? `<div class="suggestion-note">Showing ${results.length} drugs. Type to search the full database.</div>`
      : "";

  suggestions.innerHTML =
    helper +
    results
      .map((drug) => {
        const sub = drug.synonym ? `Matched synonym: ${escapeHtml(drug.synonym)}` : drug.id;
        return `
          <button class="suggestion" type="button" data-id="${escapeHtml(drug.id)}" data-name="${escapeHtml(drug.name)}">
            <strong>${escapeHtml(drug.name)}</strong>
            <small>${sub}</small>
          </button>
        `;
      })
      .join("");

  suggestions.classList.add("open");
  suggestions.querySelectorAll(".suggestion[data-id]").forEach((button) => {
    button.addEventListener("click", () => selectDrug(rowId, button.dataset.id, button.dataset.name));
  });
}

async function selectDrug(rowId, id, name) {
  const duplicate = selectedRows().find((row) => row.drug.id === id && row.rowId !== rowId);
  if (duplicate) {
    removeDrugRow(rowId);
    updateSelectedState("That drug is already in your list.");
    return;
  }

  const row = getRow(rowId);
  const picker = getPicker(rowId);
  row.drug = { id, name };
  row.detail = null;
  picker.querySelector("input").value = name;
  clearSuggestions(picker);
  state.activeBrowseId ||= id;
  await loadDrugDetail(rowId);
  updateSelectedState();
  renderDetails();
  renderBrowseTabs();
  await loadInteractionList();
}

function clearDrug(rowId) {
  const row = getRow(rowId);
  const picker = getPicker(rowId);
  const clearedId = row.drug?.id;
  row.drug = null;
  row.detail = null;
  picker.querySelector("input").value = "";
  clearSuggestions(picker);
  if (state.activeBrowseId === clearedId) {
    state.activeBrowseId = selectedRows()[0]?.drug?.id || null;
  }
  updateSelectedState();
  renderDetails();
  renderBrowseTabs();
  loadInteractionList();
}

function updateSelectedState(message = "") {
  const count = selectedRows().length;
  const possiblePairs = count > 1 ? (count * (count - 1)) / 2 : 0;
  if (message) {
    els.selectionHint.textContent = message;
  } else if (count >= 2) {
    els.selectionHint.textContent = `${count} drugs selected. ${possiblePairs} pairs will be checked.`;
  } else if (count === 1) {
    els.selectionHint.textContent = "Select one more drug.";
  } else {
    els.selectionHint.textContent = "Select at least two drugs.";
  }
}

async function loadDrugDetail(rowId) {
  const row = getRow(rowId);
  if (!row?.drug) return;
  const data = await api(`/api/drugs/${encodeURIComponent(row.drug.id)}`);
  row.detail = data.error ? null : data;
}

async function checkInteractions() {
  const selected = selectedRows();
  if (selected.length < 2) {
    els.resultPanel.innerHTML = `<p class="error">Select at least two drugs first.</p>`;
    return;
  }

  els.resultPanel.innerHTML = `<div class="empty-state"><span class="status-dot"></span><p>Checking ${selected.length} drugs...</p></div>`;
  const ids = selected.map((row) => row.drug.id).join(",");
  const data = await api(`/api/check-many?ids=${encodeURIComponent(ids)}`);
  if (data.error) {
    els.resultPanel.innerHTML = `<p class="error">${escapeHtml(data.error)}</p>`;
    return;
  }
  renderMultiResults(data);
}

function renderMultiResults(data) {
  const found = data.pairs.filter((pair) => pair.found);
  const notFound = data.pairs.filter((pair) => !pair.found);

  els.resultPanel.innerHTML = `
    <div class="summary-strip">
      <span><strong>${data.summary.selected}</strong> drugs</span>
      <span><strong>${data.summary.checked}</strong> pairs checked</span>
      <span><strong>${data.summary.found}</strong> interactions found</span>
    </div>
    <div class="result-stack">
      ${
        found.length
          ? found.map(renderPairResult).join("")
          : `<article class="result-card"><h3>No listed interactions found</h3><p class="muted">No matching pair rows were found in your local DrugBank database. This is not a clinical safety guarantee.</p></article>`
      }
      ${
        notFound.length
          ? `<details class="quiet-details"><summary>${notFound.length} pairs without a listed interaction</summary>${notFound
              .map((pair) => `<p>${escapeHtml(pair.drug1.name)} with ${escapeHtml(pair.drug2.name)}</p>`)
              .join("")}</details>`
          : ""
      }
    </div>
  `;
}

function renderPairResult(pair) {
  const interaction = pair.interaction;
  return `
    <article class="result-card">
      <div class="result-head">
        <div>
          <h3>${escapeHtml(pair.drug1.name)} + ${escapeHtml(pair.drug2.name)}</h3>
          <p>${escapeHtml(interaction.description)}</p>
        </div>
        <span class="${pillClass(interaction.severity)}">${escapeHtml(interaction.label)}</span>
      </div>
    </article>
  `;
}

function renderDetails() {
  const selected = selectedRows();
  state.textStore = {};
  state.nextTextId = 1;
  if (!selected.length) {
    els.detailsGrid.innerHTML = "";
    return;
  }
  els.detailsGrid.innerHTML = selected
    .map((row) => {
      if (!row.detail) {
        return `<article class="panel glass"><p class="muted">${escapeHtml(row.drug.name)} details loading...</p></article>`;
      }
      return `<article class="panel glass">${renderDrugDetail(row.detail)}</article>`;
    })
    .join("");
}

function renderDrugDetail(data) {
  const drug = data.drug;
  const categoryTags = data.categories
    .slice(0, 6)
    .map((category) => `<span class="pill">${escapeHtml(category)}</span>`)
    .join("");

  return `
    <div class="detail-header">
      <div>
        <h3>${escapeHtml(drug.name)}</h3>
        <p class="muted">${escapeHtml(drug.id)}</p>
      </div>
      <span class="pill">${fmt.format(data.interactionCount)} interactions</span>
    </div>
    <div class="meta-grid">
      <div class="meta-item"><span>Half-life</span>${expandableText(`${drug.name} half-life`, drug.half_life || "Not listed", 210, 3)}</div>
      <div class="meta-item"><span>Metabolism</span>${expandableText(`${drug.name} metabolism`, drug.metabolism || "Not listed", 210, 2)}</div>
    </div>
    ${drug.indication ? `<div class="text-block"><h3>Indication</h3>${expandableText(`${drug.name} indication`, drug.indication, 300, 3)}</div>` : ""}
    ${drug.mechanism ? `<div class="text-block"><h3>Mechanism</h3>${expandableText(`${drug.name} mechanism`, drug.mechanism, 300, 3)}</div>` : ""}
    ${categoryTags ? `<div class="tags">${categoryTags}</div>` : ""}
  `;
}

function renderBrowseTabs() {
  const selected = selectedRows();
  if (!selected.length) {
    els.browseTabs.innerHTML = "";
    return;
  }

  if (!selected.some((row) => row.drug.id === state.activeBrowseId)) {
    state.activeBrowseId = selected[0].drug.id;
  }

  els.browseTabs.innerHTML = selected
    .map((row) => `
      <button class="tab ${row.drug.id === state.activeBrowseId ? "active" : ""}" data-drug-id="${escapeHtml(row.drug.id)}" type="button">
        ${escapeHtml(row.drug.name)}
      </button>
    `)
    .join("");

  els.browseTabs.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeBrowseId = button.dataset.drugId;
      renderBrowseTabs();
      loadInteractionList();
    });
  });
}

async function loadInteractionList() {
  if (!state.activeBrowseId) {
    els.interactionList.innerHTML = `<p class="muted">No drug selected yet.</p>`;
    return;
  }
  const selected = selectedRows().find((row) => row.drug.id === state.activeBrowseId);
  if (!selected) return;

  const filter = els.browseFilter.value.trim();
  els.interactionList.innerHTML = `<p class="muted">Loading interactions for ${escapeHtml(selected.drug.name)}...</p>`;
  const data = await api(`/api/drugs/${encodeURIComponent(selected.drug.id)}/interactions?q=${encodeURIComponent(filter)}`);
  if (!data.results.length) {
    els.interactionList.innerHTML = `<p class="muted">No matching interactions found.</p>`;
    return;
  }
  els.interactionList.innerHTML = data.results
    .map((row) => `
      <article class="interaction-row glass">
        <div class="row-top">
          <h3>${escapeHtml(row.name)}</h3>
          <span class="${pillClass(row.severity)}">${escapeHtml(row.label)}</span>
        </div>
        <p>${escapeHtml(row.description)}</p>
      </article>
    `)
    .join("");
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("neuropharm-theme", theme);
  els.themeToggle.querySelector(".theme-icon").textContent = theme === "dark" ? "☀" : "☾";
}

document.addEventListener("click", (event) => {
  if (!event.target.closest(".drug-picker")) {
    els.drugRows.querySelectorAll(".suggestions").forEach((suggestions) => suggestions.classList.remove("open"));
  }

  const readMoreButton = event.target.closest('[data-action="read-more"]');
  if (readMoreButton) {
    const block = readMoreButton.closest(".readmore-block");
    const item = state.textStore[block.dataset.textId];
    showReaderModal(item);
  }

  if (event.target.closest('[data-action="close-reader"]')) {
    document.querySelector(".reader-modal")?.remove();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    document.querySelector(".reader-modal")?.remove();
  }
});

els.addDrugButton.addEventListener("click", () => {
  const row = addDrugRow();
  getPicker(row.rowId).querySelector("input").focus();
});

els.checkButton.addEventListener("click", checkInteractions);

els.browseFilter.addEventListener("input", () => {
  window.clearTimeout(state.searchTimers.browse);
  state.searchTimers.browse = window.setTimeout(loadInteractionList, 200);
});

els.themeToggle.addEventListener("click", () => {
  const current = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(current === "dark" ? "light" : "dark");
});

const savedTheme = localStorage.getItem("neuropharm-theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
applyTheme(savedTheme || (prefersDark ? "dark" : "light"));

addDrugRow();
addDrugRow();
loadStats().catch(() => {
  els.drugCount.textContent = "N/A";
  els.interactionCount.textContent = "N/A";
});
