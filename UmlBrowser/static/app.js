const state = {
  diagrams: [],
  filtered: [],
  current: null,
  currentSource: "",
  mode: "plantuml",
  scale: 1,
  tx: 24,
  ty: 24,
  dragging: false,
  sourceDirty: false,
  dragStart: { x: 0, y: 0, tx: 0, ty: 0 },
  renderer: null,
};

const elements = {
  diagramCount: document.querySelector("#diagramCount"),
  diagramList: document.querySelector("#diagramList"),
  diagramTitle: document.querySelector("#diagramTitle"),
  diagramPath: document.querySelector("#diagramPath"),
  rendererStatus: document.querySelector("#rendererStatus"),
  searchInput: document.querySelector("#searchInput"),
  refreshButton: document.querySelector("#refreshButton"),
  importButton: document.querySelector("#importButton"),
  messageBar: document.querySelector("#messageBar"),
  diagramStage: document.querySelector("#diagramStage"),
  diagramCanvas: document.querySelector("#diagramCanvas"),
  sourceStage: document.querySelector("#sourceStage"),
  sourceEditor: document.querySelector("#sourceEditor"),
  sourceMeta: document.querySelector("#sourceMeta"),
  saveSourceButton: document.querySelector("#saveSourceButton"),
  plantumlTab: document.querySelector("#plantumlTab"),
  previewTab: document.querySelector("#previewTab"),
  sourceTab: document.querySelector("#sourceTab"),
  zoomOutButton: document.querySelector("#zoomOutButton"),
  zoomInButton: document.querySelector("#zoomInButton"),
  fitButton: document.querySelector("#fitButton"),
  resetButton: document.querySelector("#resetButton"),
  rerenderButton: document.querySelector("#rerenderButton"),
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
  return value
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

function setMode(mode) {
  state.mode = mode;
  elements.plantumlTab.classList.toggle("active", mode === "plantuml");
  elements.previewTab.classList.toggle("active", mode === "preview");
  elements.sourceTab.classList.toggle("active", mode === "source");
  elements.diagramStage.hidden = mode === "source";
  elements.sourceStage.hidden = mode !== "source";
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
    setMessage(`${error.message} Showing Markdown preview when available.`);
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
    setMessage(`Preview from ${payload.companionPath}.`, "info");
  } catch (error) {
    clearCanvas(error.message);
    setMessage(error.message);
  }
}

function renderSource() {
  setMode("source");
  setMessage("");
  elements.sourceEditor.value = state.currentSource || "";
  elements.sourceMeta.textContent = state.current ? `${state.current.format} - ${state.current.path}` : "";
  setSourceDirty(false);
}

async function selectDiagram(diagram) {
  state.current = diagram;
  elements.diagramTitle.textContent = diagram.title;
  elements.diagramPath.textContent = diagram.path;
  renderList();
  const source = await api(`/api/source?path=${encodeURIComponent(diagram.path)}`);
  state.currentSource = source.text;
  elements.sourceEditor.value = source.text;
  elements.sourceMeta.textContent = `${source.format} - ${source.path}`;
  setSourceDirty(false);
  if (state.mode === "source") {
    renderSource();
  } else if (diagram.format === "mermaid" || state.mode === "preview" || (state.renderer && !state.renderer.available)) {
    await renderMermaidPreview(state.mode === "preview");
  } else {
    await renderPlantUml(false);
  }
}

function diagramSubtitle(diagram) {
  const bits = [diagram.plugin, diagram.kind].filter(Boolean);
  const location = bits.length ? bits.join(" / ") : diagram.fileName;
  return `${diagram.format} - ${location}`;
}

function renderList() {
  const diagrams = state.filtered.length || elements.searchInput.value.trim() ? state.filtered : state.diagrams;
  elements.diagramList.innerHTML = "";
  if (!diagrams.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No diagrams found.";
    elements.diagramList.appendChild(empty);
    return;
  }
  for (const diagram of diagrams) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "diagram-item";
    button.classList.toggle("active", state.current && state.current.path === diagram.path);
    const title = document.createElement("strong");
    title.textContent = diagram.title;
    const subtitle = document.createElement("span");
    subtitle.textContent = diagramSubtitle(diagram);
    button.append(title, subtitle);
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

async function refreshDiagrams() {
  const payload = await api("/api/diagrams");
  state.diagrams = payload.diagrams;
  state.filtered = [];
  state.renderer = payload.renderer;
  elements.diagramCount.textContent = `${payload.count} diagrams`;
  elements.rendererStatus.textContent = payload.renderer.available
    ? `${payload.umlRoot} - PlantUML renderer: ${payload.renderer.label}`
    : `${payload.umlRoot} - ${payload.renderer.reason}`;
  elements.rendererStatus.classList.toggle("warning", !payload.renderer.available);
  renderList();
  if (!state.current && state.diagrams.length) {
    await selectDiagram(state.diagrams[0]);
  }
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

elements.refreshButton.addEventListener("click", refreshDiagrams);
elements.importButton.addEventListener("click", openImportDialog);
elements.searchInput.addEventListener("input", debounce(runSearch, 180));
elements.plantumlTab.addEventListener("click", () => renderPlantUml(false));
elements.previewTab.addEventListener("click", () => renderMermaidPreview(true));
elements.sourceTab.addEventListener("click", renderSource);
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
