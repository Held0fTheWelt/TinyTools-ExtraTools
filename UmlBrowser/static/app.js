const state = {
  diagrams: [],
  filtered: [],
  compositions: [],
  compositionPayload: null,
  current: null,
  currentComposition: null,
  currentSource: "",
  currentWebPreviewUrl: "",
  explorerMode: "diagrams",
  mode: "plantuml",
  scale: 1,
  tx: 24,
  ty: 24,
  dragging: false,
  sourceDirty: false,
  dragStart: { x: 0, y: 0, tx: 0, ty: 0 },
  renderer: null,
  umlRoot: "",
};

const elements = {
  diagramCount: document.querySelector("#diagramCount"),
  diagramList: document.querySelector("#diagramList"),
  compositionList: document.querySelector("#compositionList"),
  diagramTitle: document.querySelector("#diagramTitle"),
  diagramPath: document.querySelector("#diagramPath"),
  rendererStatus: document.querySelector("#rendererStatus"),
  searchInput: document.querySelector("#searchInput"),
  refreshButton: document.querySelector("#refreshButton"),
  importButton: document.querySelector("#importButton"),
  diagramsModeButton: document.querySelector("#diagramsModeButton"),
  compositionsModeButton: document.querySelector("#compositionsModeButton"),
  diagramFilters: document.querySelector("#diagramFilters"),
  scopeFilter: document.querySelector("#scopeFilter"),
  familyFilter: document.querySelector("#familyFilter"),
  groupFilter: document.querySelector("#groupFilter"),
  messageBar: document.querySelector("#messageBar"),
  diagramStage: document.querySelector("#diagramStage"),
  diagramCanvas: document.querySelector("#diagramCanvas"),
  modelStage: document.querySelector("#modelStage"),
  modelPanel: document.querySelector("#modelPanel"),
  sourceStage: document.querySelector("#sourceStage"),
  sourceEditor: document.querySelector("#sourceEditor"),
  sourceMeta: document.querySelector("#sourceMeta"),
  saveSourceButton: document.querySelector("#saveSourceButton"),
  compositionStage: document.querySelector("#compositionStage"),
  compositionPanel: document.querySelector("#compositionPanel"),
  plantumlTab: document.querySelector("#plantumlTab"),
  previewTab: document.querySelector("#previewTab"),
  modelTab: document.querySelector("#modelTab"),
  sourceTab: document.querySelector("#sourceTab"),
  compositionTab: document.querySelector("#compositionTab"),
  zoomOutButton: document.querySelector("#zoomOutButton"),
  zoomInButton: document.querySelector("#zoomInButton"),
  fitButton: document.querySelector("#fitButton"),
  resetButton: document.querySelector("#resetButton"),
  rerenderButton: document.querySelector("#rerenderButton"),
  openSvgButton: document.querySelector("#openSvgButton"),
  webPreviewButton: document.querySelector("#webPreviewButton"),
  fullscreenButton: document.querySelector("#fullscreenButton"),
  importDialog: document.querySelector("#importDialog"),
  importForm: document.querySelector("#importForm"),
  importPath: document.querySelector("#importPath"),
  importSource: document.querySelector("#importSource"),
  importOverwrite: document.querySelector("#importOverwrite"),
  cancelImportButton: document.querySelector("#cancelImportButton"),
  secondaryCancelImportButton: document.querySelector("#secondaryCancelImportButton"),
};

let mermaidModule = null;

async function api(path) {
  const response = await fetch(path, { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok && !payload.ok) {
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
  if (!response.ok && !payload.ok) {
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

function updateToolbarState() {
  const hasDiagram = Boolean(state.current);
  const diagramView = hasDiagram && ["plantuml", "preview"].includes(state.mode);
  for (const button of [elements.zoomOutButton, elements.zoomInButton, elements.fitButton, elements.resetButton, elements.fullscreenButton]) {
    button.disabled = !diagramView;
  }
  elements.rerenderButton.disabled = !hasDiagram || state.current.format !== "plantuml";
  elements.openSvgButton.disabled = !hasDiagram || state.current.format !== "plantuml";
  elements.webPreviewButton.disabled = !hasDiagram || state.current.format !== "plantuml" || !state.currentWebPreviewUrl;
}

function setMode(mode) {
  state.mode = mode;
  elements.plantumlTab.classList.toggle("active", mode === "plantuml");
  elements.previewTab.classList.toggle("active", mode === "preview");
  elements.modelTab.classList.toggle("active", mode === "model");
  elements.sourceTab.classList.toggle("active", mode === "source");
  elements.compositionTab.classList.toggle("active", mode === "composition");
  elements.diagramStage.hidden = !["plantuml", "preview"].includes(mode);
  elements.modelStage.hidden = mode !== "model";
  elements.sourceStage.hidden = mode !== "source";
  elements.compositionStage.hidden = mode !== "composition";
  updateToolbarState();
}

function setExplorerMode(mode, render = true) {
  state.explorerMode = mode;
  const compositionMode = mode === "compositions";
  elements.diagramsModeButton.classList.toggle("active", !compositionMode);
  elements.compositionsModeButton.classList.toggle("active", compositionMode);
  elements.diagramFilters.hidden = compositionMode;
  elements.diagramList.hidden = compositionMode;
  elements.compositionList.hidden = !compositionMode;
  elements.importButton.disabled = compositionMode;
  elements.searchInput.placeholder = compositionMode ? "status, tool, value" : "class, route, plugin";
  if (render) {
    if (compositionMode) {
      setMessage("");
      renderCompositionList();
      updateCompositionStatus();
      if (!state.currentComposition && state.compositions.length) {
        selectComposition(state.compositions[0].id);
      }
    } else {
      renderList();
      updateDiagramStatus();
      if (!state.current && state.diagrams.length) {
        selectDiagram(state.diagrams[0]);
      }
    }
  }
}

function setSourceDirty(dirty) {
  state.sourceDirty = dirty;
  elements.saveSourceButton.disabled = !dirty || !state.current;
  elements.saveSourceButton.textContent = dirty ? "Save Source *" : "Save Source";
}

function applyTransform() {
  elements.diagramCanvas.style.transform = `translate(${state.tx}px, ${state.ty}px) scale(${state.scale})`;
}

function clearCanvas(text = "") {
  elements.diagramCanvas.innerHTML = text ? `<div class="empty-state">${escapeHtml(text)}</div>` : "";
  state.scale = 1;
  state.tx = 24;
  state.ty = 24;
  applyTransform();
}

function parseSvgSize(svg) {
  const viewBox = svg.viewBox && svg.viewBox.baseVal;
  if (viewBox && viewBox.width > 0 && viewBox.height > 0) {
    return { width: viewBox.width, height: viewBox.height };
  }
  const parse = (value) => {
    const match = String(value || "").match(/[\d.]+/);
    return match ? Number(match[0]) : 0;
  };
  return {
    width: parse(svg.getAttribute("width")) || svg.getBoundingClientRect().width || 1000,
    height: parse(svg.getAttribute("height")) || svg.getBoundingClientRect().height || 800,
  };
}

function fitToView() {
  const svg = elements.diagramCanvas.querySelector("svg");
  if (!svg) return;
  const viewport = elements.diagramStage.getBoundingClientRect();
  const size = parseSvgSize(svg);
  const padding = 32;
  const scale = Math.min(
    (viewport.width - padding) / size.width,
    (viewport.height - padding) / size.height,
    2,
  );
  state.scale = Math.max(0.05, scale);
  state.tx = Math.max(16, (viewport.width - size.width * state.scale) / 2);
  state.ty = Math.max(16, (viewport.height - size.height * state.scale) / 2);
  applyTransform();
}

function zoomAt(factor, clientX, clientY) {
  const rect = elements.diagramStage.getBoundingClientRect();
  const px = clientX - rect.left;
  const py = clientY - rect.top;
  const beforeX = (px - state.tx) / state.scale;
  const beforeY = (py - state.ty) / state.scale;
  state.scale = Math.min(8, Math.max(0.03, state.scale * factor));
  state.tx = px - beforeX * state.scale;
  state.ty = py - beforeY * state.scale;
  applyTransform();
}

function viewportCenter() {
  const rect = elements.diagramStage.getBoundingClientRect();
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  };
}

function setSvg(svgText) {
  elements.diagramCanvas.innerHTML = svgText;
  const svg = elements.diagramCanvas.querySelector("svg");
  if (svg) {
    svg.removeAttribute("style");
    svg.setAttribute("preserveAspectRatio", "xMinYMin meet");
  }
  requestAnimationFrame(fitToView);
}

async function loadMermaid() {
  if (mermaidModule) return mermaidModule;
  const module = await import("https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs");
  mermaidModule = module.default;
  mermaidModule.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "base",
    themeVariables: {
      fontFamily: "Segoe UI, Arial, sans-serif",
      primaryColor: "#ffffff",
      primaryBorderColor: "#9aa7b7",
      primaryTextColor: "#151922",
      lineColor: "#475569",
      secondaryColor: "#d8f3ee",
      tertiaryColor: "#f7f8fa",
    },
  });
  return mermaidModule;
}

async function renderPlantUml(force = false) {
  if (!state.current) return;
  if (state.current.format === "mermaid") {
    await renderMermaidPreview(true);
    return;
  }
  setMode("plantuml");
  setMessage("");
  clearCanvas("Rendering PlantUML...");
  try {
    const payload = await api(`/api/render?path=${encodeURIComponent(state.current.path)}&force=${force ? "1" : "0"}`);
    if (payload.ok) {
      setSvg(payload.svg);
      setMessage(payload.cached ? "Loaded cached PlantUML SVG." : `Rendered PlantUML SVG in ${payload.elapsedMs || 0} ms.`, "info");
      return;
    }
    throw new Error(payload.error || "PlantUML render failed.");
  } catch (error) {
    const suffix = state.currentWebPreviewUrl ? " PlantUML Web is available from the Web button." : "";
    setMessage(`${error.message} Showing Markdown preview when available.${suffix}`);
    await renderMermaidPreview(false);
  }
}

async function renderMermaidPreview(makeActive = true) {
  if (!state.current) return;
  if (makeActive) setMode("preview");
  clearCanvas("Rendering preview...");
  try {
    const payload = await api(`/api/mermaid?path=${encodeURIComponent(state.current.path)}`);
    if (!payload.ok) {
      throw new Error(payload.error || "No Mermaid preview.");
    }
    const mermaid = await loadMermaid();
    const renderId = `uml-preview-${Date.now()}`;
    const result = await mermaid.render(renderId, payload.code);
    setSvg(result.svg);
    const origin = payload.companionPath || payload.path || "diagram source";
    setMessage(`Preview from ${origin}.`, "info");
  } catch (error) {
    clearCanvas(error.message);
    setMessage(error.message);
  }
}

function renderSource() {
  if (!state.current) return;
  setMode("source");
  setMessage("");
  elements.sourceEditor.value = state.currentSource || "";
  elements.sourceMeta.textContent = `${state.current.format} - ${state.current.path}`;
  setSourceDirty(false);
}

function panelSection(title, bodyHtml) {
  return `<section class="panel-section"><h3>${escapeHtml(title)}</h3>${bodyHtml}</section>`;
}

function metrics(items) {
  return `<div class="metric-grid">${items
    .map((item) => `<div class="metric"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></div>`)
    .join("")}</div>`;
}

function renderTable(columns, rows, emptyText) {
  if (!rows.length) {
    return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
  }
  return `<table class="data-table"><thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead><tbody>${rows
    .map(
      (row) =>
        `<tr>${columns
          .map((column) => `<td>${escapeHtml(typeof column.value === "function" ? column.value(row) : row[column.value])}</td>`)
          .join("")}</tr>`,
    )
    .join("")}</tbody></table>`;
}

async function renderModel() {
  if (!state.current) return;
  setMode("model");
  setMessage("");
  elements.modelPanel.innerHTML = panelSection("Model", `<div class="empty-state">Reading model...</div>`);
  try {
    const payload = await api(`/api/model?path=${encodeURIComponent(state.current.path)}`);
    const warningHtml = payload.warnings.length
      ? panelSection("Warnings", `<ul class="warning-list">${payload.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`)
      : "";
    const relatedHtml = payload.related.length
      ? panelSection(
          "Related Diagrams",
          `<div class="related-grid">${payload.related
            .map((diagram) => `<button type="button" data-diagram-path="${escapeHtml(diagram.path)}">${escapeHtml(diagram.title)}</button>`)
            .join("")}</div>`,
        )
      : "";
    elements.modelPanel.innerHTML = [
      panelSection(
        "Summary",
        metrics([
          { label: "Source", value: payload.sourceType },
          { label: "Elements", value: payload.elements.length },
          { label: "Relationships", value: payload.relationships.length },
          { label: "Lines", value: payload.lineCount },
          { label: "Companion", value: payload.companionPath || "none" },
        ]),
      ),
      relatedHtml,
      warningHtml,
      panelSection(
        "Elements",
        renderTable(
          [
            { label: "Kind", value: "kind" },
            { label: "Name", value: "label" },
            { label: "Package", value: "package" },
            { label: "Line", value: "line" },
          ],
          payload.elements,
          "No elements recognized.",
        ),
      ),
      panelSection(
        "Relationships",
        renderTable(
          [
            { label: "Source", value: "source" },
            { label: "Kind", value: "kind" },
            { label: "Target", value: "target" },
            { label: "Label", value: "label" },
            { label: "Line", value: "line" },
          ],
          payload.relationships,
          "No relationships recognized.",
        ),
      ),
    ].join("");
  } catch (error) {
    elements.modelPanel.innerHTML = panelSection("Model", `<div class="empty-state">${escapeHtml(error.message)}</div>`);
    setMessage(error.message);
  }
}

async function selectDiagram(diagram, preferredMode = null) {
  state.current = diagram;
  state.currentComposition = null;
  elements.compositionTab.hidden = true;
  elements.diagramTitle.textContent = diagram.title;
  elements.diagramPath.textContent = diagram.path;
  renderList();
  try {
    const source = await api(`/api/source?path=${encodeURIComponent(diagram.path)}`);
    state.currentSource = source.text;
    state.currentWebPreviewUrl = source.webPreviewUrl || "";
    elements.sourceEditor.value = source.text;
    elements.sourceMeta.textContent = `${source.format} - ${source.path}`;
    setSourceDirty(false);
    const nextMode = preferredMode || (state.mode === "composition" ? "plantuml" : state.mode);
    if (nextMode === "source") {
      renderSource();
    } else if (nextMode === "model") {
      await renderModel();
    } else if (diagram.format === "mermaid" || nextMode === "preview" || (state.renderer && !state.renderer.available)) {
      await renderMermaidPreview(nextMode === "preview");
    } else {
      await renderPlantUml(false);
    }
  } catch (error) {
    setMessage(error.message);
  }
}

function diagramSubtitle(diagram) {
  const bits = [diagram.group, diagram.family].filter(Boolean);
  return `${diagram.format} - ${bits.join(" / ") || diagram.fileName}`;
}

function currentDiagramSet() {
  const query = elements.searchInput.value.trim();
  let diagrams = query ? state.filtered : state.diagrams;
  const scope = elements.scopeFilter.value;
  const family = elements.familyFilter.value;
  const group = elements.groupFilter.value;
  if (scope !== "all") diagrams = diagrams.filter((diagram) => diagram.scope === scope);
  if (family !== "all") diagrams = diagrams.filter((diagram) => diagram.family === family);
  if (group !== "all") diagrams = diagrams.filter((diagram) => diagram.group === group);
  return diagrams;
}

function renderList() {
  const diagrams = currentDiagramSet();
  elements.diagramList.innerHTML = "";
  if (!diagrams.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No diagrams found.";
    elements.diagramList.appendChild(empty);
    return;
  }
  const grouped = new Map();
  for (const diagram of diagrams) {
    const key = `${diagram.group} / ${diagram.family}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(diagram);
  }
  for (const [groupName, groupDiagrams] of grouped) {
    const heading = document.createElement("div");
    heading.className = "list-group-title";
    heading.textContent = groupName;
    elements.diagramList.appendChild(heading);
    for (const diagram of groupDiagrams) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "diagram-item";
      button.classList.toggle("active", state.current && state.current.path === diagram.path);
      const title = document.createElement("strong");
      title.textContent = diagram.title;
      const subtitle = document.createElement("span");
      subtitle.textContent = diagramSubtitle(diagram);
      const badges = document.createElement("div");
      badges.className = "diagram-badges";
      for (const label of [diagram.scope, diagram.hasCompanion ? "md" : "", diagram.isLibrary ? "library" : ""]) {
        if (!label) continue;
        const badge = document.createElement("span");
        badge.className = "badge";
        badge.textContent = label;
        badges.appendChild(badge);
      }
      button.append(title, subtitle, badges);
      if (diagram.matchCount) {
        const matchCount = document.createElement("span");
        matchCount.textContent = `${diagram.matchCount} matches`;
        button.appendChild(matchCount);
        for (const match of diagram.matches || []) {
          const line = document.createElement("div");
          line.className = "match-line";
          line.textContent = `${match.fileKind}:${match.line} ${match.text}`;
          button.appendChild(line);
        }
      }
      button.addEventListener("click", () => selectDiagram(diagram));
      elements.diagramList.appendChild(button);
    }
  }
}

function setSelectOptions(select, values, allLabel) {
  const current = select.value;
  select.innerHTML = `<option value="all">${escapeHtml(allLabel)}</option>${values
    .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    .join("")}`;
  select.value = values.includes(current) ? current : "all";
}

function updateFilters() {
  const families = [...new Set(state.diagrams.map((diagram) => diagram.family).filter(Boolean))].sort();
  const groups = [...new Set(state.diagrams.map((diagram) => diagram.group).filter(Boolean))].sort();
  setSelectOptions(elements.familyFilter, families, "All families");
  setSelectOptions(elements.groupFilter, groups, "All groups");
}

function updateDiagramStatus() {
  elements.diagramCount.textContent = `${state.diagrams.length} diagrams`;
  elements.rendererStatus.textContent = state.renderer && state.renderer.available
    ? `${state.umlRoot} - PlantUML renderer: ${state.renderer.label}`
    : `${state.umlRoot} - ${state.renderer ? state.renderer.reason : "Renderer status unknown"}`;
  elements.rendererStatus.classList.toggle("warning", Boolean(state.renderer && !state.renderer.available));
}

function updateCompositionStatus() {
  const payload = state.compositionPayload;
  elements.diagramCount.textContent = `${state.compositions.length} compositions`;
  const warnings = payload && payload.warnings && payload.warnings.length ? ` - ${payload.warnings[0]}` : "";
  elements.rendererStatus.textContent = payload ? `Composition source: ${payload.source}${warnings}` : "Composition source not loaded.";
  elements.rendererStatus.classList.toggle("warning", Boolean(payload && payload.warnings && payload.warnings.length));
}

async function refreshDiagrams() {
  const payload = await api("/api/diagrams");
  state.diagrams = payload.diagrams;
  state.filtered = [];
  state.renderer = payload.renderer;
  state.umlRoot = payload.umlRoot;
  updateFilters();
  updateDiagramStatus();
  renderList();
  await refreshCompositions(false);
  if (!state.current && state.diagrams.length) {
    await selectDiagram(state.diagrams[0]);
  }
  if (state.explorerMode === "compositions") {
    updateCompositionStatus();
    renderCompositionList();
  }
}

async function refreshCompositions(applyStatus = true) {
  const query = state.explorerMode === "compositions" ? elements.searchInput.value.trim() : "";
  const payload = await api(`/api/compositions?q=${encodeURIComponent(query)}`);
  state.compositionPayload = payload;
  state.compositions = payload.compositions || [];
  if (applyStatus) updateCompositionStatus();
  renderCompositionList();
}

async function saveSource() {
  if (!state.current) return;
  setMessage("");
  try {
    const payload = await postApi("/api/source", {
      path: state.current.path,
      text: elements.sourceEditor.value,
    });
    state.currentSource = payload.text;
    state.currentWebPreviewUrl = payload.webPreviewUrl || "";
    state.current = { ...state.current, title: payload.title, format: payload.format };
    elements.diagramTitle.textContent = payload.title;
    setSourceDirty(false);
    setMessage(`Saved ${payload.path}.`, "info");
  } catch (error) {
    setMessage(error.message);
  }
}

function openImportDialog() {
  elements.importDialog.hidden = false;
  elements.importPath.focus();
  elements.importPath.select();
}

function closeImportDialog() {
  elements.importDialog.hidden = true;
}

async function importDiagram(event) {
  event.preventDefault();
  setMessage("");
  try {
    const payload = await postApi("/api/import", {
      path: elements.importPath.value.trim(),
      text: elements.importSource.value,
      overwrite: elements.importOverwrite.checked,
    });
    closeImportDialog();
    await refreshDiagrams();
    const imported = state.diagrams.find((diagram) => diagram.path === payload.diagram.path);
    if (imported) {
      await selectDiagram(imported);
    }
    setMessage(`Imported ${payload.diagram.path}.`, "info");
  } catch (error) {
    setMessage(error.message);
  }
}

async function runSearch() {
  const query = elements.searchInput.value.trim();
  if (state.explorerMode === "compositions") {
    await refreshCompositions(true);
    return;
  }
  if (!query) {
    state.filtered = [];
    renderList();
    return;
  }
  const payload = await api(`/api/search?q=${encodeURIComponent(query)}&limit=200`);
  state.filtered = payload.results;
  renderList();
}

function debounce(callback, delay) {
  let timer = 0;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => callback(...args), delay);
  };
}

function renderCompositionList() {
  elements.compositionList.innerHTML = "";
  if (!state.compositions.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No compositions found.";
    elements.compositionList.appendChild(empty);
    return;
  }
  for (const composition of state.compositions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "diagram-item";
    button.classList.toggle("active", state.currentComposition && state.currentComposition.id === composition.id);
    const title = document.createElement("strong");
    title.textContent = composition.title;
    const subtitle = document.createElement("span");
    subtitle.textContent = `${composition.level} - ${composition.mode}`;
    const badges = document.createElement("div");
    badges.className = "diagram-badges";
    for (const label of [composition.status, ...composition.tools.slice(0, 3)]) {
      if (!label) continue;
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = label;
      badges.appendChild(badge);
    }
    const summary = document.createElement("small");
    summary.textContent = composition.valueSummary || "";
    button.append(title, subtitle, badges, summary);
    button.addEventListener("click", () => selectComposition(composition.id));
    elements.compositionList.appendChild(button);
  }
}

function renderLinkChips(items) {
  if (!items || !items.length) return `<span class="badge">none</span>`;
  return `<div class="link-list">${items.map((item) => `<span>${escapeHtml(item.label || item.path)}<br><small>${escapeHtml(item.path || "")}</small></span>`).join("")}</div>`;
}

function renderTools(items) {
  if (!items || !items.length) return `<span class="badge">none</span>`;
  return `<div class="tool-list">${items.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

async function selectComposition(compositionId) {
  try {
    const payload = await api(`/api/composition?id=${encodeURIComponent(compositionId)}`);
    const composition = payload.composition;
    setMessage("");
    state.currentComposition = composition;
    state.current = null;
    elements.compositionTab.hidden = false;
    elements.diagramTitle.textContent = composition.title;
    elements.diagramPath.textContent = `${composition.level} - ${composition.status}`;
    setMode("composition");
    renderCompositionList();
    renderCompositionDetail(composition, payload.warnings || []);
  } catch (error) {
    setMessage(error.message);
  }
}

function renderCompositionDetail(composition, warnings) {
  const warningHtml = warnings.length
    ? panelSection("Warnings", `<ul class="warning-list">${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`)
    : "";
  const diagramHtml = composition.diagramInfos && composition.diagramInfos.length
    ? `<div class="related-grid">${composition.diagramInfos
        .map((diagram) => `<button type="button" data-diagram-path="${escapeHtml(diagram.path)}">${escapeHtml(diagram.title)}</button>`)
        .join("")}</div>`
    : renderLinkChips(composition.diagrams);
  elements.compositionPanel.innerHTML = [
    `<section class="panel-section composition-hero"><h3>${escapeHtml(composition.title)}</h3><p>${escapeHtml(composition.valueSummary)}</p>${metrics([
      { label: "Status", value: composition.status },
      { label: "Level", value: composition.level },
      { label: "Mode", value: composition.mode },
      { label: "Source", value: composition.sourcePath || "manifest" },
    ])}</section>`,
    panelSection("Tools", renderTools(composition.tools)),
    panelSection("Required", renderTools(composition.requiredTools)),
    panelSection("Optional", renderTools(composition.optionalTools)),
    panelSection("UML Views", diagramHtml),
    panelSection("Docs", renderLinkChips(composition.docs)),
    panelSection("Owning SAD Decisions", renderLinkChips(composition.owningSadDecisions)),
    panelSection("Contracts", renderLinkChips(composition.contracts)),
    panelSection("Gates", renderLinkChips(composition.gates)),
    panelSection("Evidence", renderLinkChips(composition.evidence)),
    panelSection("Limits", renderTools(composition.limits)),
    warningHtml,
  ].join("");
}

function openSvg() {
  if (!state.current || state.current.format !== "plantuml") return;
  window.open(`/api/svg?path=${encodeURIComponent(state.current.path)}`, "_blank", "noopener");
}

function openWebPreview() {
  if (!state.currentWebPreviewUrl) return;
  window.open(state.currentWebPreviewUrl, "_blank", "noopener");
}

function toggleFullscreen() {
  const target = elements.diagramStage;
  if (document.fullscreenElement === target) {
    document.exitFullscreen();
    return;
  }
  if (target.requestFullscreen) {
    target.requestFullscreen();
  }
}

elements.refreshButton.addEventListener("click", refreshDiagrams);
elements.importButton.addEventListener("click", openImportDialog);
elements.diagramsModeButton.addEventListener("click", () => setExplorerMode("diagrams"));
elements.compositionsModeButton.addEventListener("click", () => setExplorerMode("compositions"));
elements.searchInput.addEventListener("input", debounce(runSearch, 180));
elements.scopeFilter.addEventListener("change", renderList);
elements.familyFilter.addEventListener("change", renderList);
elements.groupFilter.addEventListener("change", renderList);
elements.plantumlTab.addEventListener("click", () => renderPlantUml(false));
elements.previewTab.addEventListener("click", () => renderMermaidPreview(true));
elements.modelTab.addEventListener("click", renderModel);
elements.sourceTab.addEventListener("click", renderSource);
elements.compositionTab.addEventListener("click", () => {
  if (state.currentComposition) {
    setMode("composition");
  }
});
elements.saveSourceButton.addEventListener("click", saveSource);
elements.sourceEditor.addEventListener("input", () => setSourceDirty(elements.sourceEditor.value !== state.currentSource));
elements.importForm.addEventListener("submit", importDiagram);
elements.cancelImportButton.addEventListener("click", closeImportDialog);
elements.secondaryCancelImportButton.addEventListener("click", closeImportDialog);
elements.zoomInButton.addEventListener("click", () => {
  const center = viewportCenter();
  zoomAt(1.18, center.x, center.y);
});
elements.zoomOutButton.addEventListener("click", () => {
  const center = viewportCenter();
  zoomAt(1 / 1.18, center.x, center.y);
});
elements.fitButton.addEventListener("click", fitToView);
elements.resetButton.addEventListener("click", () => {
  state.scale = 1;
  state.tx = 24;
  state.ty = 24;
  applyTransform();
});
elements.rerenderButton.addEventListener("click", () => renderPlantUml(true));
elements.openSvgButton.addEventListener("click", openSvg);
elements.webPreviewButton.addEventListener("click", openWebPreview);
elements.fullscreenButton.addEventListener("click", toggleFullscreen);

elements.diagramStage.addEventListener("wheel", (event) => {
  event.preventDefault();
  zoomAt(event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX, event.clientY);
}, { passive: false });

elements.diagramStage.addEventListener("pointerdown", (event) => {
  elements.diagramStage.setPointerCapture(event.pointerId);
  state.dragging = true;
  state.dragStart = { x: event.clientX, y: event.clientY, tx: state.tx, ty: state.ty };
  elements.diagramStage.classList.add("dragging");
});

elements.diagramStage.addEventListener("pointermove", (event) => {
  if (!state.dragging) return;
  state.tx = state.dragStart.tx + event.clientX - state.dragStart.x;
  state.ty = state.dragStart.ty + event.clientY - state.dragStart.y;
  applyTransform();
});

elements.diagramStage.addEventListener("pointerup", (event) => {
  state.dragging = false;
  elements.diagramStage.releasePointerCapture(event.pointerId);
  elements.diagramStage.classList.remove("dragging");
});

elements.diagramStage.addEventListener("pointercancel", () => {
  state.dragging = false;
  elements.diagramStage.classList.remove("dragging");
});

elements.modelPanel.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-diagram-path]");
  if (!button) return;
  const diagram = state.diagrams.find((item) => item.path === button.dataset.diagramPath);
  if (diagram) {
    setExplorerMode("diagrams", false);
    await selectDiagram(diagram, "plantuml");
    setExplorerMode("diagrams", false);
  }
});

elements.compositionPanel.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-diagram-path]");
  if (!button) return;
  const diagram = state.diagrams.find((item) => item.path === button.dataset.diagramPath);
  if (diagram) {
    setExplorerMode("diagrams", false);
    await selectDiagram(diagram, "plantuml");
    setExplorerMode("diagrams", false);
  }
});

document.addEventListener("fullscreenchange", () => {
  const active = document.fullscreenElement === elements.diagramStage;
  elements.diagramStage.classList.toggle("is-fullscreen", active);
  elements.fullscreenButton.textContent = active ? "Exit" : "Full";
  window.setTimeout(fitToView, 80);
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !elements.importDialog.hidden) {
    closeImportDialog();
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && state.mode === "source") {
    event.preventDefault();
    saveSource();
  }
});

refreshDiagrams().catch((error) => {
  setMessage(error.message);
  clearCanvas(error.message);
});
