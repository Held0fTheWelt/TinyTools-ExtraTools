use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

/// Directory holding the Python toolchain (`trace_for_editor.py`, the venv…).
/// Overridable with TRACK_SHAPE_DIR; otherwise resolved relative to this crate
/// (editor/src-tauri -> ../../../TrackShape).
fn track_shape_dir() -> PathBuf {
    if let Ok(p) = std::env::var("TRACK_SHAPE_DIR") {
        return PathBuf::from(p);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../TrackShape")
}

/// Python interpreter that runs the tracer. Prefers TRACK_SHAPE_PYTHON, then the
/// project venv, then whatever `python`/`python3` is on PATH.
fn resolve_python(dir: &PathBuf) -> PathBuf {
    if let Ok(p) = std::env::var("TRACK_SHAPE_PYTHON") {
        return PathBuf::from(p);
    }
    let win = dir.join(".venv/Scripts/python.exe");
    if win.exists() {
        return win;
    }
    let posix = dir.join(".venv/bin/python");
    if posix.exists() {
        return posix;
    }
    PathBuf::from(if cfg!(windows) { "python" } else { "python3" })
}

fn run_python_tool(script_name: &str, request: serde_json::Value, label: &str) -> Result<serde_json::Value, String> {
    let dir = track_shape_dir();
    let py = resolve_python(&dir);
    let script = dir.join(script_name);

    let mut child = Command::new(&py)
        .arg(&script)
        .current_dir(&dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Python konnte nicht gestartet werden ({}): {e}", py.display()))?;

    {
        let stdin = child.stdin.as_mut().ok_or("stdin nicht verfügbar")?;
        let body = serde_json::to_vec(&request).map_err(|e| e.to_string())?;
        stdin.write_all(&body).map_err(|e| e.to_string())?;
    }

    let out = child.wait_with_output().map_err(|e| e.to_string())?;
    if !out.status.success() && out.stdout.is_empty() {
        return Err(format!(
            "{label}-Fehler: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    serde_json::from_slice(&out.stdout).map_err(|e| {
        format!(
            "{label}-Ausgabe unlesbar: {e}: {}",
            String::from_utf8_lossy(&out.stderr)
        )
    })
}

/// Trace a two-color image into a `track_shape.v1`, auto-scaled to the target
/// length. The heavy lifting lives in the same Python one-shot the browser path
/// uses; here we just pipe the request to its stdin and relay its stdout.
#[tauri::command]
fn trace_image(request: serde_json::Value) -> Result<serde_json::Value, String> {
    run_python_tool("trace_for_editor.py", request, "Tracer")
}

#[tauri::command]
fn apply_to_unreal(request: serde_json::Value) -> Result<serde_json::Value, String> {
    run_python_tool("apply_for_editor.py", request, "Unreal-Apply")
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![trace_image, apply_to_unreal])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
