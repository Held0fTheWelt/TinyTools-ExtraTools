# Track Shape Editor — Desktop (Tauri) build

This is the **optional** native-desktop wrapper. It has the exact same features
as the browser editor, including **Load image...** with automatic scaling, but
in a native window, fully offline, with no dev server in a browser tab.

The browser path (`npm run dev`) needs **none** of this. Use Tauri only if you
want the standalone app.

## How it works

The same React UI runs in a native webview. The **Load image...** button calls a
Rust command `trace_image` (in `src-tauri/src/lib.rs`), which runs the same
`../../TrackShape/trace_for_editor.py` the browser path uses — so the tracer,
auto-detection of the two colors, and the auto-scaling to your target length are
identical. No separate server, no open port.

## One-time prerequisites (Windows)

Tauri compiles a small Rust binary, so it needs a toolchain you don't have yet:

1. **Rust** — install from <https://rustup.rs> (run `rustup-init.exe`, accept defaults).
2. **Visual Studio C++ Build Tools** — the "Desktop development with C++"
   workload. rustup will point you to it if missing. (Several GB, one-time.)
3. Verify in a **new** terminal: `cargo --version` prints a version.

## Run it

From this `editor/` folder, in **Windows** PowerShell/cmd (so `node_modules`
and the build match Windows):

```powershell
npm install              # pulls @tauri-apps/cli; installs Windows-native deps
npm run tauri dev        # opens the desktop app (first build is slow: Rust compiles)
```

To produce an installer/executable:

```powershell
npm run tauri build      # output under src-tauri/target/release/bundle/
```

## Configuration knobs

The Rust command finds Python and the toolchain automatically:

- `TRACK_SHAPE_PYTHON` — path to the Python interpreter (default: the project
  venv `../../TrackShape/.venv/Scripts/python.exe`, else `python` on PATH).
- `TRACK_SHAPE_DIR` — path to the Python toolchain folder (default: `../../TrackShape`).

Icons live in `src-tauri/icons/` (regenerate any time with
`npx tauri icon path\to\source.png`).

## Notes

- The Python venv at `../../TrackShape/.venv` must exist (it already does).
- First `tauri dev` compiles Rust dependencies and can take a few minutes;
  later runs are fast.
- Everything for the Tauri path is Windows-native (node + Rust + the Python
  venv), which sidesteps the WSL/Windows split the browser path bridges.
