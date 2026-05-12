const state = {
  a: null,
  b: null,
  browseTab: "a",
  searchTimers: {},
};

const els = {
  drugCount: document.querySelector("#drugCount"),
  interactionCount: document.querySelector("#interactionCount"),
  drugA: document.querySelector("#drugA"),
  drugB: document.querySelector("#drugB"),
  suggestionsA: document.querySelector("#suggestionsA"),
  suggestionsB: document.querySelector("#suggestionsB"),
  checkButton: document.querySelector("#checkButton"),
  swapButton: document.querySelector("#swapButton"),
  selectionHint: document.querySelector("#selectionHint"),
  resultPanel: document.querySelector("#resultPanel"),
  detailA: document.querySelector("#detailA"),
  detailB: document.querySelector("#detailB"),
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

function setupPicker(key, input, suggestions) {
  input.addEventListener("input", () => {
    state[key] = null;
    updateHint();
    window.clearTimeout(state.searchTimers[key]);
    const q = input.value.trim();
    if (q.length < 2) {
      suggestions.classList.remove("open");
      suggestions.innerHTML = "";
      return;
    }
    state.searchTimers[key] = window.setTimeout(() => searchDrugs(key, q), 180);
  });

  input.addEventListener("focus", () => {
    if (suggestions.innerHTML) suggestions.classList.add("open");
  });
}

async function searchDrugs(key, q) {
  const suggestions = key === "a" ? els.suggestionsA : els.suggestionsB;
  const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
  if (!data.results.length) {
    suggestions.innerHTML = `<div class="suggestion"><strong>No matches</strong><small>Try another spelling or synonym.</small></div>`;
    suggestions.classList.add("open");
    return;
  }
  suggestions.innerHTML = data.results
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
    button.addEventListener("click", () => selectDrug(key, button.dataset.id, button.dataset.name));
  });
}

async function selectDrug(key, id, name) {
  state[key] = { id, name };
  const input = key === "a" ? els.drugA : els.drugB;
  const suggestions = key === "a" ? els.suggestionsA : els.suggestionsB;
  input.value = name;
  suggestions.classList.remove("open");
  suggestions.innerHTML = "";
  updateHint();
  await loadDrugDetail(key);
  if (state.a && state.b) await checkInteraction();
  await loadInteractionList();
}

function clearDrug(key) {
  state[key] = null;
  const input = key === "a" ? els.drugA : els.drugB;
  const detail = key === "a" ? els.detailA : els.detailB;
  input.value = "";
  detail.innerHTML = `<p class="muted">Drug ${key.toUpperCase()} details</p>`;
  updateHint();
  loadInteractionList();
}

function updateHint() {
  if (state.a && state.b) {
    els.selectionHint.textContent = "Ready to check this pair.";
  } else if (state.a || state.b) {
    els.selectionHint.textContent = "Select one more drug.";
  } else {
    els.selectionHint.textContent = "Start typing at least two letters.";
  }
}

async function checkInteraction() {
  if (!state.a || !state.b) {
    els.resultPanel.innerHTML = `<p class="error">Select two drugs first.</p>`;
    return;
  }
  const data = await api(`/api/check?drug1=${encodeURIComponent(state.a.id)}&drug2=${encodeURIComponent(state.b.id)}`);
  if (data.error) {
    els.resultPanel.innerHTML = `<p class="error">${escapeHtml(data.error)}</p>`;
    return;
  }
  renderResult(data);
}

function renderResult(data) {
  const a = data.drug1;
  const b = data.drug2;
  if (!data.found) {
    els.resultPanel.innerHTML = `
      <div class="result-card">
        <div class="result-head">
          <div>
            <h3>No listed interaction found</h3>
            <div class="drug-pair"><strong>${escapeHtml(a.name)}</strong><span>with</span><strong>${escapeHtml(b.name)}</strong></div>
          </div>
          <span class="severity none">No match in database</span>
        </div>
        <p class="muted">This means no matching interaction row was found in the local DrugBank database. It is not a clinical safety guarantee.</p>
      </div>
    `;
    return;
  }

  const interaction = data.interaction;
  els.resultPanel.innerHTML = `
    <div class="result-card">
      <div class="result-head">
        <div>
          <h3>Interaction listed</h3>
          <div class="drug-pair"><strong>${escapeHtml(a.name)}</strong><span>with</span><strong>${escapeHtml(b.name)}</strong></div>
        </div>
        <span class="${pillClass(interaction.severity)}">${escapeHtml(interaction.label)}</span>
      </div>
      <p>${escapeHtml(interaction.description)}</p>
    </div>
  `;
}

async function loadDrugDetail(key) {
  const selected = state[key];
  if (!selected) return;
  const panel = key === "a" ? els.detailA : els.detailB;
  panel.innerHTML = `<p class="muted">Loading ${escapeHtml(selected.name)}...</p>`;
  const data = await api(`/api/drugs/${encodeURIComponent(selected.id)}`);
  if (data.error) {
    panel.innerHTML = `<p class="error">${escapeHtml(data.error)}</p>`;
    return;
  }
  panel.innerHTML = renderDrugDetail(data);
}

function renderDrugDetail(data) {
  const drug = data.drug;
  const categoryTags = data.categories
    .slice(0, 8)
    .map((category) => `<span class="pill">${escapeHtml(category)}</span>`)
    .join("");
  const food = data.foodInteractions
    .map((item) => `<p class="text-block">${escapeHtml(item)}</p>`)
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
      <div class="meta-item"><span>Half-life</span>${escapeHtml(drug.half_life || "Not listed")}</div>
      <div class="meta-item"><span>Metabolism</span>${escapeHtml(drug.metabolism || "Not listed")}</div>
    </div>
    ${drug.indication ? `<div class="text-block"><h3>Indication</h3><p>${escapeHtml(drug.indication)}</p></div>` : ""}
    ${drug.mechanism ? `<div class="text-block"><h3>Mechanism</h3><p>${escapeHtml(drug.mechanism)}</p></div>` : ""}
    ${categoryTags ? `<div class="tags">${categoryTags}</div>` : ""}
    ${food ? `<div class="text-block"><h3>Food interactions</h3>${food}</div>` : ""}
  `;
}

async function loadInteractionList() {
  const selected = state[state.browseTab];
  const filter = els.browseFilter.value.trim();
  if (!selected) {
    els.interactionList.innerHTML = `<p class="muted">No drug selected yet.</p>`;
    return;
  }
  els.interactionList.innerHTML = `<p class="muted">Loading interactions for ${escapeHtml(selected.name)}...</p>`;
  const data = await api(`/api/drugs/${encodeURIComponent(selected.id)}/interactions?q=${encodeURIComponent(filter)}`);
  if (!data.results.length) {
    els.interactionList.innerHTML = `<p class="muted">No matching interactions found.</p>`;
    return;
  }
  els.interactionList.innerHTML = data.results
    .map((row) => `
      <article class="interaction-row">
        <div class="row-top">
          <h3>${escapeHtml(row.name)}</h3>
          <span class="${pillClass(row.severity)}">${escapeHtml(row.label)}</span>
        </div>
        <p>${escapeHtml(row.description)}</p>
      </article>
    `)
    .join("");
}

function swapDrugs() {
  const oldA = state.a;
  state.a = state.b;
  state.b = oldA;
  els.drugA.value = state.a?.name || "";
  els.drugB.value = state.b?.name || "";
  loadDrugDetail("a");
  loadDrugDetail("b");
  updateHint();
  if (state.a && state.b) checkInteraction();
  loadInteractionList();
}

document.addEventListener("click", (event) => {
  if (!event.target.closest(".drug-picker")) {
    els.suggestionsA.classList.remove("open");
    els.suggestionsB.classList.remove("open");
  }
});

document.querySelectorAll("[data-clear]").forEach((button) => {
  button.addEventListener("click", () => clearDrug(button.dataset.clear));
});

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    state.browseTab = button.dataset.tab;
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab === button));
    loadInteractionList();
  });
});

setupPicker("a", els.drugA, els.suggestionsA);
setupPicker("b", els.drugB, els.suggestionsB);
els.checkButton.addEventListener("click", checkInteraction);
els.swapButton.addEventListener("click", swapDrugs);
els.browseFilter.addEventListener("input", () => {
  window.clearTimeout(state.searchTimers.browse);
  state.searchTimers.browse = window.setTimeout(loadInteractionList, 200);
});

loadStats().catch(() => {
  els.drugCount.textContent = "N/A";
  els.interactionCount.textContent = "N/A";
});
