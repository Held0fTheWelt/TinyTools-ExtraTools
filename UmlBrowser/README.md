# Tiny Tool UML Browser

Local browser for PlantUML and Mermaid diagram folders.

When the repository-level `UML/` folder is available it is used by default. When
the tool is copied elsewhere, it falls back to the bundled `samples/` folder so
the browser is usable immediately without the original project.

## Start with Docker status window

Recommended:

```powershell
.\Tools\UmlBrowser\start_uml_browser.cmd
```

This opens a visible PowerShell status window, builds the Docker image, replaces any previous `tinytool-uml-browser` container, deploys a fresh one, and stays attached to the container logs. The window prints the URL, usually `http://127.0.0.1:8765`.

Stop it with `Ctrl+C` in that status window.

From an existing PowerShell terminal you can run the same workflow without opening a new window:

```powershell
.\Tools\UmlBrowser\run_uml_browser.ps1
```

Use another port when needed:

```powershell
.\Tools\UmlBrowser\run_uml_browser.ps1 -Port 8877
```

The Docker image installs Java, Graphviz, and a pinned PlantUML jar inside the container. Your host only needs Docker Desktop. The default PlantUML version is set in [Dockerfile](Dockerfile) via `PLANTUML_VERSION`.

Update the bundled PlantUML version by changing `PLANTUML_VERSION` and `PLANTUML_SHA256` in the Dockerfile, then run the script again.

## Start without Docker

```powershell
python Tools\UmlBrowser\uml_browser.py
```

Open `http://127.0.0.1:8765`.

Use the bundled standalone samples explicitly:

```powershell
python uml_browser.py --uml-root samples
```

## Rendering

The browser indexes `.puml`, `.uml`, `.mmd`, and `.mermaid` files.

The Docker workflow can render `.puml` and `.uml` files to cached SVG immediately because PlantUML is installed inside the container.

The non-Docker Python workflow can render when PlantUML is available locally:

- `plantuml` on `PATH`; or
- `PLANTUML_CMD` with the full command; or
- `PLANTUML_JAR` pointing to `plantuml.jar` and `java` on `PATH`; or
- `--plantuml C:\path\to\plantuml.jar`.

Rendered SVG files are cached under `Saved/UmlBrowser/svg/`, which is already outside the versioned UML source tree.

Mermaid files render directly in the browser preview tab. For PlantUML diagrams,
when PlantUML is not available, the UI falls back to the first fenced `mermaid`
preview from the same-basename Markdown companion. The Mermaid renderer is loaded
in the browser from jsDelivr; diagram source is still served only by the local
Python process.

## Import and update diagrams

Use **Import** in the sidebar to paste a new PlantUML or Mermaid diagram into the
active UML root. Target paths must stay below that root and use one of:

- `.puml`
- `.uml`
- `.mmd`
- `.mermaid`

Open the **Source** tab to edit the selected diagram in place. `Ctrl+S` saves the
source while that tab is active. Rendered PlantUML SVG caches are invalidated
after a source save.

## Manual Java and PlantUML setup on Windows

Only use this path if you want to run the browser without Docker. Install a current Java runtime:

```powershell
winget install --id EclipseAdoptium.Temurin.21.JRE --exact
```

Close and reopen PowerShell, then verify:

```powershell
java -version
```

Download `plantuml.jar` from the official PlantUML download page:

- https://plantuml.com/download

Keep the jar outside the tracked source tree, for example:

```powershell
New-Item -ItemType Directory -Force -Path Saved\UmlBrowser
# Put plantuml.jar into Saved\UmlBrowser\plantuml.jar
```

Start the browser with the jar:

```powershell
python Tools\UmlBrowser\uml_browser.py --plantuml Saved\UmlBrowser\plantuml.jar
```

Or set it once for the current PowerShell session:

```powershell
$env:PLANTUML_JAR = "D:\TinyToolDevelopment\Git\Saved\UmlBrowser\plantuml.jar"
python Tools\UmlBrowser\uml_browser.py
```

If PlantUML later reports a Graphviz or `dot` problem, install Graphviz and reopen PowerShell:

```powershell
winget install --id Graphviz.Graphviz --exact
dot -V
```

## Useful commands

```powershell
python Tools\UmlBrowser\uml_browser.py --port 8877
python Tools\UmlBrowser\uml_browser.py --plantuml C:\Tools\plantuml.jar
python Tools\UmlBrowser\uml_browser.py --uml-root UML --cache-root Saved\UmlBrowser
python Tools\UmlBrowser\uml_browser.py --uml-root Tools\UmlBrowser\samples
```
