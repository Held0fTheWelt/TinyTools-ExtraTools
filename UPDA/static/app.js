const state = {
  overview: null,
  items: [],
  current: null,
  currentDetail: null,
  planning: null,
  deploys: [],
  activePackageId: "",
  view: "overview",
  selected: new Set(),
  filters: {
    q: "",
    kind: "all",
    status: "all",
    tag: "all",
  },
};

const elements = {
  sidebarStatus: document.querySelector("#sidebarStatus"),
  refreshButton: document.querySelector("#refreshButton"),
  sectionTabs: Array.from(document.querySelectorAll(".section-tab")),
  searchInput: document.querySelector("#searchInput"),
  kindFilter: document.querySelector("#kindFilter"),
  statusFilter: document.querySelector("#statusFilter"),
  tagFilter: document.querySelector("#tagFilter"),
  selectionCount: document.querySelector("#selectionCount"),
  clearSelectionButton: document.querySelector("#clearSelectionButton"),
  itemList: document.querySelector("#itemList"),
  viewTitle: document.querySelector("#viewTitle"),
  viewSubtitle: document.querySelector("#viewSubtitle"),
  selectCurrentButton: document.querySelector("#selectCurrentButton"),
  packageSelectionButton: document.querySelector("#packageSelectionButton"),
  messageBar: document.querySelector("#messageBar"),
  overviewView: document.querySelector("#overviewView"),
  reviewView: document.querySelector("#reviewView"),
  planningView: document.querySelector("#planningView"),
  deployView: document.querySelector("#deployView"),
  packageDialog: document.querySelector("#packageDialog"),
  packageForm: document.querySelector("#packageForm"),
  closePackageDialogButton: document.querySelector("#closePackageDialogButton"),
  cancelPackageButton: document.querySelector("#cancelPackageButton"),
  packageTitleInput: document.querySelector("#packageTitleInput"),
  packagePriorityInput: document.querySelector("#packagePriorityInput"),
  packageStatusInput: document.querySelector("#packageStatusInput"),
  packageNotesInput: document.querySelector("#packageNotesInput"),
};

async function api(path) {
  const response = await fetch(path, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || response.statusText);
  }
  return payload;
}

async function postApi(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || response.statusText);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setMessage(message, tone = "warning") {
  if (!message) {
    elements.messageBar.hidden = true;
    elements.messageBar.textContent = "";
    return;
  }
  elements.messageBar.hidden = false;
  elements.messageBar.textContent = message;
  elements.messageBar.dataset.tone = tone;
}

function optionHtml(value, label, current) {
  return `<option value="${escapeHtml(value)}"${value === current ? " selected" : ""}>${escapeHtml(label)}</option>`;
}

function populateFilters(filters) {
  const kindOptions = [optionHtml("all", "All kinds", state.filters.kind)]
    .concat((filters.kinds || []).map((item) => optionHtml(item.value, item.label, state.filters.kind)));
  elements.kindFilter.innerHTML = kindOptions.join("");

  const statusOptions = [optionHtml("all", "All statuses", state.filters.status)]
    .concat((filters.statuses || []).map((item) => optionHtml(item, item, state.filters.status)));
  elements.statusFilter.innerHTML = statusOptions.join("");

  const tagOptions = [optionHtml("all", "All tags", state.filters.tag)]
    .concat((filters.tags || []).slice(0, 260).map((item) => optionHtml(item, item, state.filters.tag)));
  elements.tagFilter.innerHTML = tagOptions.join("");
}

function metricPanel(value, label, tone = "") {
  return `
    <article class="panel span-3 ${tone}">
      <div class="metric-value">${escapeHtml(value)}</div>
      <div class="metric-label">${escapeHtml(label)}</div>
    </article>
  `;
}

function badges(values, extraClass = "") {
  const clean = (values || []).filter(Boolean);
  if (!clean.length) return `<span class="badge empty">none</span>`;
  return clean.map((value) => `<span class="badge ${extraClass}">${escapeHtml(value)}</span>`).join("");
}

function setView(view) {
  state.view = view;
  for (const tab of elements.sectionTabs) {
    tab.classList.toggle("active", tab.dataset.view === view);
  }
  for (const panel of [elements.overviewView, elements.reviewView, elements.planningView, elements.deployView]) {
    panel.classList.remove("active-view");
  }
  document.querySelector(`#${view}View`).classList.add("active-view");
  const labels = {
    overview: ["Overview", "Blueprint Journal sources, project cases, and index health"],
    review: ["Review", "Search and understand Blueprint Journals and BPJ knowledge"],
    planning: ["Planning", "Organize journal records into project work packages"],
    deploy: ["Deploy", "Generate implementation-preparation plans from journal packages"],
  };
  elements.viewTitle.textContent = labels[view][0];
  elements.viewSubtitle.textContent = labels[view][1];
  if (view === "review" && !state.current && state.items.length) {
    selectItem(state.items[0].id);
  }
  renderAll();
}

function queryString() {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(state.filters)) {
    if (value) params.set(key, value);
  }
  return params.toString();
}

async function loadOverview() {
  const payload = await api("/api/overview");
  state.overview = payload.overview;
  populateFilters(payload.filters || {});
}

async function loadItems() {
  const payload = await api(`/api/items?${queryString()}`);
  state.items = payload.items || [];
  elements.sidebarStatus.textContent = `${payload.count} of ${payload.total} records`;
  populateFilters(payload.filters || {});
  renderItemList();
}

async function loadPlanning() {
  const payload = await api("/api/planning");
  state.planning = payload.planning;
  const packages = state.planning.packages || [];
  if (!state.activePackageId && packages.length) {
    state.activePackageId = packages[0].id;
  }
}

async function loadDeploys() {
  const payload = await api("/api/deploy");
  state.deploys = payload.deploys || [];
}

async function selectItem(id) {
  const record = state.items.find((item) => item.id === id) || state.current;
  state.current = record;
  renderItemList();
  try {
    const payload = await api(`/api/item?id=${encodeURIComponent(id)}`);
    state.currentDetail = payload.item;
    state.current = payload.item;
    renderReview();
    updateSelectionState();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

function toggleCurrentSelection() {
  if (!state.current) return;
  if (state.selected.has(state.current.id)) {
    state.selected.delete(state.current.id);
  } else {
    state.selected.add(state.current.id);
  }
  updateSelectionState();
  renderItemList();
  renderReview();
}

function updateSelectionState() {
  elements.selectionCount.textContent = `${state.selected.size} selected`;
  elements.selectCurrentButton.disabled = !state.current;
  elements.selectCurrentButton.textContent = state.current && state.selected.has(state.current.id) ? "Unselect Record" : "Select Record";
  elements.packageSelectionButton.disabled = state.selected.size === 0;
}

function renderItemList() {
  if (!state.items.length) {
    elements.itemList.innerHTML = `<div class="empty-state">No records match the current filters.</div>`;
    updateSelectionState();
    return;
  }
  elements.itemList.innerHTML = state.items.map((item) => {
    const active = state.current && state.current.id === item.id ? " active" : "";
    const selected = state.selected.has(item.id) ? " selected" : "";
    const status = item.status ? `<span class="badge status">${escapeHtml(item.status)}</span>` : "";
    const project = item.project ? `<span>${escapeHtml(item.project)}</span>` : "";
    const flags = item.section_flags || {};
    const flagLabels = Object.entries(flags)
      .filter(([, value]) => value)
      .map(([key]) => key.replaceAll("_", " "));
    return `
      <div class="item-row${active}${selected}" data-id="${escapeHtml(item.id)}" role="button" tabindex="0">
        <div class="item-title">
          <strong>${escapeHtml(item.title)}</strong>
          <span class="badge kind">${escapeHtml(item.kind_label)}</span>
        </div>
        <span>${escapeHtml(item.rel_path)}</span>
        <div class="badge-row">
          ${status}
          ${state.selected.has(item.id) ? `<span class="badge">selected</span>` : ""}
          ${flagLabels.slice(0, 2).map((label) => `<span class="badge">${escapeHtml(label)}</span>`).join("")}
        </div>
        ${project}
      </div>
    `;
  }).join("");
  updateSelectionState();
}

function renderOverview() {
  const overview = state.overview;
  if (!overview) {
    elements.overviewView.innerHTML = `<div class="empty-state">Overview loading...</div>`;
    return;
  }
  const sourceRows = (overview.sources || []).map((source) => `
    <tr>
      <td>${escapeHtml(source.label)}</td>
      <td>${source.exists ? "yes" : "no"}</td>
      <td>${escapeHtml(source.count)}</td>
      <td><code>${escapeHtml(source.rel_path || source.path)}</code></td>
    </tr>
  `).join("");
  const kindRows = Object.entries(overview.by_kind || {}).map(([kind, count]) => `
    <tr>
      <td>${escapeHtml(kind.replaceAll("_", " "))}</td>
      <td>${escapeHtml(count)}</td>
    </tr>
  `).join("");
  const workflow = (overview.workflow || []).map((step) => `
    <article class="panel span-3">
      <h3>${escapeHtml(step.name)}</h3>
      <p class="text-block">${escapeHtml(step.purpose)}</p>
    </article>
  `).join("");
  elements.overviewView.innerHTML = `
    <div class="view-grid">
      ${metricPanel(overview.journal_projects, "Journal projects")}
      ${metricPanel(overview.project_journals, "Project journals")}
      ${metricPanel(overview.knowledge_journals, "Knowledge records")}
      ${metricPanel(overview.planning_packages, "Planning packages")}
      ${workflow}
      <section class="panel span-12">
        <h3>Journal Projects</h3>
        <table class="source-table">
          <thead><tr><th>Project</th><th>Status</th><th>Focus</th><th>Source Project</th><th>Journal</th></tr></thead>
          <tbody>${(overview.projects || []).map((project) => `
            <tr>
              <td>${escapeHtml(project.name)}</td>
              <td>${escapeHtml(project.status || "")}</td>
              <td>${escapeHtml(project.focus || "")}</td>
              <td><code>${escapeHtml(project.source_project || "")}</code></td>
              <td><code>${escapeHtml(project.rel_path || "")}</code></td>
            </tr>
          `).join("") || `<tr><td colspan="5">No project journals found.</td></tr>`}</tbody>
        </table>
      </section>
      <section class="panel span-5">
        <h3>Index Mix</h3>
        <table class="source-table">
          <thead><tr><th>Kind</th><th>Count</th></tr></thead>
          <tbody>${kindRows}</tbody>
        </table>
      </section>
      <section class="panel span-7">
        <h3>Local State</h3>
        <div class="kv-grid">
          <div class="kv"><span>Workspace</span><strong>${escapeHtml(overview.workspace_root)}</strong></div>
          <div class="kv"><span>State root</span><strong>${escapeHtml(overview.state_root)}</strong></div>
        </div>
      </section>
      <section class="panel span-12">
        <h3>Sources</h3>
        <table class="source-table">
          <thead><tr><th>Source</th><th>Exists</th><th>Records</th><th>Path</th></tr></thead>
          <tbody>${sourceRows}</tbody>
        </table>
      </section>
    </div>
  `;
}

function markdownLite(text) {
  if (!text || !String(text).trim()) {
    return `<p class="empty-state">No section content.</p>`;
  }
  const lines = String(text).split(/\r?\n/);
  let html = "";
  let index = 0;

  const parseTable = () => {
    const tableLines = [];
    while (index < lines.length && lines[index].trim().startsWith("|")) {
      tableLines.push(lines[index].trim());
      index += 1;
    }
    if (tableLines.length < 2) return "";
    const rows = tableLines
      .filter((line, rowIndex) => rowIndex !== 1)
      .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()));
    const header = rows.shift() || [];
    const head = `<thead><tr>${header.map((cell) => `<th>${escapeHtml(cell)}</th>`).join("")}</tr></thead>`;
    const body = `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`).join("")}</tbody>`;
    return `<table>${head}${body}</table>`;
  };

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();
    if (!trimmed) {
      index += 1;
      continue;
    }
    if (trimmed.startsWith("```")) {
      index += 1;
      const code = [];
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      html += `<pre>${escapeHtml(code.join("\n"))}</pre>`;
      continue;
    }
    if (trimmed.startsWith("|") && lines[index + 1] && lines[index + 1].includes("---")) {
      html += parseTable();
      continue;
    }
    const heading = trimmed.match(/^(#{2,5})\s+(.+)$/);
    if (heading) {
      html += `<h4>${escapeHtml(heading[2])}</h4>`;
      index += 1;
      continue;
    }
    if (/^[-*]\s+/.test(trimmed)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ""));
        index += 1;
      }
      html += `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
      continue;
    }
    const paragraph = [trimmed];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^[-*]\s+/.test(lines[index].trim()) && !lines[index].trim().startsWith("|")) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    html += `<p>${escapeHtml(paragraph.join(" "))}</p>`;
  }
  return html;
}

function renderFieldGrid(item) {
  const pairs = Object.entries(item.fields || {}).filter(([, value]) => value);
  if (!pairs.length && !Object.keys(item.metrics || {}).length) return "";
  const metricPairs = Object.entries(item.metrics || {}).filter(([, value]) => value !== "" && value !== null && value !== undefined);
  return `
    <section class="panel span-12">
      <h3>Record Facts</h3>
      <div class="kv-grid">
        ${pairs.map(([key, value]) => `<div class="kv"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
        ${metricPairs.map(([key, value]) => `<div class="kv"><span>${escapeHtml(key.replaceAll("_", " "))}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
      </div>
    </section>
  `;
}

function sectionPanel(title, value) {
  if (!value) return "";
  return `
    <section class="panel span-12">
      <h3>${escapeHtml(title)}</h3>
      <div class="text-block">${markdownLite(value)}</div>
    </section>
  `;
}

function renderReview() {
  const item = state.currentDetail || state.current;
  if (!item) {
    elements.reviewView.innerHTML = `<div class="empty-state">Select a record from the left index.</div>`;
    return;
  }
  const sections = item.sections || {};
  elements.reviewView.innerHTML = `
    <div class="view-grid">
      <section class="panel span-12">
        <div class="detail-header">
          <div>
            <h3>${escapeHtml(item.title)}</h3>
            <div class="detail-meta">
              <span>${escapeHtml(item.rel_path)}</span>
              <span>${escapeHtml(item.source_label || "")}</span>
            </div>
          </div>
          <div class="badge-row">
            ${badges([item.kind_label], "kind")}
            ${item.status ? badges([item.status], "status") : ""}
            ${badges((item.tags || []).slice(0, 16))}
          </div>
          <p class="text-block">${escapeHtml(item.excerpt || "No excerpt available.")}</p>
        </div>
      </section>
      ${renderFieldGrid(item)}
      ${sectionPanel("Evidence Snapshot", sections.evidence_snapshot)}
      ${sectionPanel("Construction Instructions", sections.construction_instructions)}
      ${sectionPanel("Specification Backlog", sections.specification_backlog)}
      ${sectionPanel("Open Evidence Requests", sections.open_evidence_requests)}
      ${sectionPanel("Blueprint Surface Functions", sections.function_summary)}
      <section class="panel span-12">
        <h3>Source Preview</h3>
        <pre class="code-preview">${escapeHtml(item.content_preview || "")}</pre>
      </section>
    </div>
  `;
}

function activePackage() {
  const packages = state.planning?.packages || [];
  return packages.find((item) => item.id === state.activePackageId) || packages[0] || null;
}

function packageItemRows(pkg) {
  const items = pkg.items || [];
  if (!items.length) return `<div class="empty-state">No records in this package yet.</div>`;
  return items.map((item) => `
    <div class="item-row" data-id="${escapeHtml(item.id)}" role="button" tabindex="0">
      <div class="item-title">
        <strong>${escapeHtml(item.title)}</strong>
        <span class="badge kind">${escapeHtml(item.kind_label)}</span>
      </div>
      <span>${escapeHtml(item.rel_path)}</span>
    </div>
  `).join("");
}

function renderPlanning() {
  const planning = state.planning;
  if (!planning) {
    elements.planningView.innerHTML = `<div class="empty-state">Planning loading...</div>`;
    return;
  }
  const packages = planning.packages || [];
  const pkg = activePackage();
  const packageRows = packages.length ? packages.map((item) => `
    <button class="package-row${item.id === (pkg && pkg.id) ? " active" : ""}" data-package-id="${escapeHtml(item.id)}" type="button">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.priority || "P1")} / ${escapeHtml(item.status || "draft")} / ${(item.items || []).length} records</span>
    </button>
  `).join("") : `<div class="empty-state">No planning packages yet.</div>`;

  const editor = pkg ? `
    <div class="inline-editor" data-editor-package-id="${escapeHtml(pkg.id)}">
      <label>Title <input id="editPackageTitle" value="${escapeHtml(pkg.title || "")}"></label>
      <div class="modal-grid">
        <label>Priority
          <select id="editPackagePriority">
            ${["P0", "P1", "P2", "P3"].map((value) => optionHtml(value, value, pkg.priority || "P1")).join("")}
          </select>
        </label>
        <label>Status
          <select id="editPackageStatus">
            ${["draft", "review", "ready", "deployed"].map((value) => optionHtml(value, value, pkg.status || "draft")).join("")}
          </select>
        </label>
      </div>
      <label>Notes <textarea id="editPackageNotes">${escapeHtml(pkg.notes || "")}</textarea></label>
      <div class="button-row">
        <button id="savePackageButton" class="tool-button primary" type="button">Save Package</button>
        <button id="addSelectionToPackageButton" class="tool-button" type="button"${state.selected.size ? "" : " disabled"}>Add Selection</button>
        <button id="deployPackageButton" class="tool-button" type="button">Create Deploy Plan</button>
        <button id="deletePackageButton" class="tool-button" type="button">Delete</button>
      </div>
    </div>
  ` : `<div class="empty-state">Create a package from the current selection.</div>`;

  elements.planningView.innerHTML = `
    <div class="view-grid">
      <section class="panel span-4">
        <div class="row-actions">
          <button id="newPackageFromSelectionButton" class="tool-button primary" type="button"${state.selected.size ? "" : " disabled"}>Package Selection</button>
        </div>
        <h3>Packages</h3>
        <div class="package-list">${packageRows}</div>
      </section>
      <section class="panel span-8">
        <h3>Package Detail</h3>
        ${editor}
      </section>
      <section class="panel span-12">
        <h3>Package Records</h3>
        <div class="item-list">${pkg ? packageItemRows(pkg) : `<div class="empty-state">No package selected.</div>`}</div>
      </section>
    </div>
  `;

  elements.planningView.querySelector("#newPackageFromSelectionButton")?.addEventListener("click", openPackageDialog);
  for (const row of elements.planningView.querySelectorAll("[data-package-id]")) {
    row.addEventListener("click", () => {
      state.activePackageId = row.dataset.packageId;
      renderPlanning();
    });
  }
  elements.planningView.querySelector("#savePackageButton")?.addEventListener("click", saveActivePackage);
  elements.planningView.querySelector("#deletePackageButton")?.addEventListener("click", deleteActivePackage);
  elements.planningView.querySelector("#addSelectionToPackageButton")?.addEventListener("click", addSelectionToActivePackage);
  elements.planningView.querySelector("#deployPackageButton")?.addEventListener("click", () => createDeployPlan(pkg.id));
  for (const row of elements.planningView.querySelectorAll(".item-row[data-id]")) {
    row.addEventListener("click", () => {
      setView("review");
      selectItem(row.dataset.id);
    });
  }
}

function renderDeploy() {
  const planning = state.planning;
  const packages = planning?.packages || [];
  const deployRows = state.deploys.length ? state.deploys.map((deploy) => `
    <tr>
      <td>${escapeHtml(deploy.name)}</td>
      <td>${escapeHtml(deploy.modified)}</td>
      <td>${escapeHtml(deploy.bytes)}</td>
      <td><code>${escapeHtml(deploy.rel_path)}</code></td>
    </tr>
  `).join("") : `<tr><td colspan="4">No deploy plans created yet.</td></tr>`;
  const packageRows = packages.length ? packages.map((pkg) => `
    <tr>
      <td>${escapeHtml(pkg.title)}</td>
      <td>${escapeHtml(pkg.priority || "P1")}</td>
      <td>${escapeHtml(pkg.status || "draft")}</td>
      <td>${(pkg.items || []).length}</td>
      <td><button class="tool-button primary" data-deploy-package="${escapeHtml(pkg.id)}" type="button">Generate</button></td>
    </tr>
  `).join("") : `<tr><td colspan="5">Create a planning package first.</td></tr>`;
  elements.deployView.innerHTML = `
    <div class="view-grid">
      <section class="panel span-12">
        <h3>Generate From Package</h3>
        <table class="source-table">
          <thead><tr><th>Package</th><th>Priority</th><th>Status</th><th>Records</th><th>Action</th></tr></thead>
          <tbody>${packageRows}</tbody>
        </table>
      </section>
      <section class="panel span-12">
        <h3>Recent Deploy Plans</h3>
        <table class="source-table">
          <thead><tr><th>Name</th><th>Modified</th><th>Bytes</th><th>Path</th></tr></thead>
          <tbody>${deployRows}</tbody>
        </table>
      </section>
    </div>
  `;
  for (const button of elements.deployView.querySelectorAll("[data-deploy-package]")) {
    button.addEventListener("click", () => createDeployPlan(button.dataset.deployPackage));
  }
}

function renderAll() {
  renderOverview();
  renderReview();
  renderPlanning();
  renderDeploy();
  updateSelectionState();
}

function openPackageDialog() {
  if (!state.selected.size) return;
  const selectedTitles = state.items.filter((item) => state.selected.has(item.id)).slice(0, 2).map((item) => item.title);
  elements.packageTitleInput.value = selectedTitles.length ? selectedTitles.join(" + ") : "UPDA planning package";
  elements.packagePriorityInput.value = "P1";
  elements.packageStatusInput.value = "draft";
  elements.packageNotesInput.value = "";
  elements.packageDialog.hidden = false;
  elements.packageTitleInput.focus();
}

function closePackageDialog() {
  elements.packageDialog.hidden = true;
}

async function createPackageFromDialog(event) {
  event.preventDefault();
  try {
    const payload = await postApi("/api/planning/create", {
      title: elements.packageTitleInput.value,
      priority: elements.packagePriorityInput.value,
      status: elements.packageStatusInput.value,
      notes: elements.packageNotesInput.value,
      item_ids: Array.from(state.selected),
    });
    state.planning = payload.planning;
    state.activePackageId = payload.package.id;
    closePackageDialog();
    setMessage("Planning package created.", "ok");
    setView("planning");
    renderPlanning();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function saveActivePackage() {
  const pkg = activePackage();
  if (!pkg) return;
  try {
    const payload = await postApi("/api/planning/update", {
      id: pkg.id,
      title: elements.planningView.querySelector("#editPackageTitle").value,
      priority: elements.planningView.querySelector("#editPackagePriority").value,
      status: elements.planningView.querySelector("#editPackageStatus").value,
      notes: elements.planningView.querySelector("#editPackageNotes").value,
      item_ids: pkg.item_ids || [],
    });
    state.planning = payload.planning;
    setMessage("Package saved.", "ok");
    renderPlanning();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function addSelectionToActivePackage() {
  const pkg = activePackage();
  if (!pkg || !state.selected.size) return;
  const itemIds = new Set(pkg.item_ids || []);
  for (const id of state.selected) itemIds.add(id);
  try {
    const payload = await postApi("/api/planning/update", {
      id: pkg.id,
      item_ids: Array.from(itemIds),
    });
    state.planning = payload.planning;
    setMessage("Selection added to package.", "ok");
    renderPlanning();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function deleteActivePackage() {
  const pkg = activePackage();
  if (!pkg) return;
  try {
    const payload = await postApi("/api/planning/delete", { id: pkg.id });
    state.planning = payload.planning;
    state.activePackageId = "";
    setMessage("Package deleted.", "ok");
    renderPlanning();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function createDeployPlan(packageId) {
  if (!packageId) return;
  try {
    const payload = await postApi("/api/deploy/create", { package_id: packageId });
    state.deploys = payload.deploys;
    await loadPlanning();
    setMessage(`Deploy plan created: ${payload.deploy.rel_path}`, "ok");
    setView("deploy");
    renderDeploy();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

async function refreshIndex() {
  setMessage("Refreshing index...", "warning");
  try {
    await api("/api/reindex");
    await loadOverview();
    await loadItems();
    await loadPlanning();
    await loadDeploys();
    setMessage("Index refreshed.", "ok");
    renderAll();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

let searchTimer = 0;

function wireEvents() {
  for (const tab of elements.sectionTabs) {
    tab.addEventListener("click", () => setView(tab.dataset.view));
  }
  elements.refreshButton.addEventListener("click", refreshIndex);
  elements.searchInput.addEventListener("input", () => {
    state.filters.q = elements.searchInput.value;
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(async () => {
      await loadItems();
      renderAll();
    }, 180);
  });
  for (const select of [elements.kindFilter, elements.statusFilter, elements.tagFilter]) {
    select.addEventListener("change", async () => {
      state.filters.kind = elements.kindFilter.value;
      state.filters.status = elements.statusFilter.value;
      state.filters.tag = elements.tagFilter.value;
      await loadItems();
      renderAll();
    });
  }
  elements.itemList.addEventListener("click", (event) => {
    const row = event.target.closest(".item-row[data-id]");
    if (row) {
      setView("review");
      selectItem(row.dataset.id);
    }
  });
  elements.itemList.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest(".item-row[data-id]");
    if (row) {
      event.preventDefault();
      setView("review");
      selectItem(row.dataset.id);
    }
  });
  elements.selectCurrentButton.addEventListener("click", toggleCurrentSelection);
  elements.packageSelectionButton.addEventListener("click", openPackageDialog);
  elements.clearSelectionButton.addEventListener("click", () => {
    state.selected.clear();
    updateSelectionState();
    renderItemList();
    renderReview();
  });
  elements.packageForm.addEventListener("submit", createPackageFromDialog);
  elements.closePackageDialogButton.addEventListener("click", closePackageDialog);
  elements.cancelPackageButton.addEventListener("click", closePackageDialog);
}

async function init() {
  wireEvents();
  try {
    await loadOverview();
    await loadItems();
    await loadPlanning();
    await loadDeploys();
    renderAll();
    setMessage("");
  } catch (error) {
    setMessage(error.message, "error");
  }
}

init();
