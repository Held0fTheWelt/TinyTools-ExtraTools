# Example: wave plan JSON embedded in Markdown

Paste or generate a block like this next to your wave-plan table; `wave_plan_emit.py md2json --embed` extracts it.

```json
{
  "schema_version": "1",
  "ds_id": "DS-099",
  "slug": "backend_runtime_services",
  "session_date": "20260410",
  "completed_wave_ids": ["w01"],
  "next_index": 2,
  "sub_waves": [
    {
      "index": 1,
      "id": "w01",
      "goal": "Extract helper module for first seam; keep public API unchanged.",
      "primary_paths": ["backend/app/__init__.py"],
      "gate_commands": ["python \"./'fy'-suites/despaghettify/tools/ds005_runtime_import_check.py\""]
    },
    {
      "index": 2,
      "id": "w02",
      "goal": "Thin entrypoint and wire imports.",
      "primary_paths": ["backend/app/__init__.py"],
      "gate_commands": ["python \"./'fy'-suites/despaghettify/tools/ds005_runtime_import_check.py\""]
    }
  ]
}
```
