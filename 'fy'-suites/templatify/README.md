# Templatify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is **template integration governance** for HTML/Jinja surfaces: it inventories template inheritance, maps stable target blocks, and can generate or apply an area-specific shell integration **without rewriting page content templates**.

## What Templatify is responsible for

- **Template inventory** for repository HTML/Jinja surfaces.
- **Area-aware integration plans** for `frontend`, `administration-tool`, `backend` info pages, `writers-room`, and similar surfaces.
- **Source-pack driven shell generation** from a designer-owned template folder.
- **Safe base-template adaptation**: child page templates may remain unchanged while base templates are regenerated to extend the integrated shell.
- **Reports and state** so template integration is restartable, inspectable, and reviewable.

## What Templatify is not responsible for

- Rewriting the business/content blocks of page templates.
- Acting as a CSS framework or component library.
- Guessing arbitrary design intent from screenshots alone.
- Replacing frontend implementation review.

## Source pack idea

Templatify expects a **source folder** owned by design or product. That folder can contain one generic shell or multiple area-specific shells. The shell uses explicit slot tokens such as `[[TITLE]]`, `[[CONTENT]]`, `[[EXTRA_HEAD]]`, or `[[HEADER]]`.

Templatify then maps those canonical slots to the **existing block names** of the target area, so pages like `frontend/templates/dashboard.html` or `administration-tool/templates/forum/index.html` can keep their content blocks as they are.

## Layout

| Path | Role |
|------|------|
| [`tools/`](tools/) | Python package for inventory, planning, generation, and apply mode |
| [`templates/source_pack/`](templates/source_pack/) | Example source-pack layout with shell placeholders |
| [`reports/`](reports/) | JSON + markdown plan and inventory outputs |
| [`state/`](state/) | Stable restartable state files |
| [`generated/`](generated/) | Default output root for generated overlays and patch previews |

## Main commands

```bash
templatify inspect
templatify plan --source-dir path/to/source-pack
templatify apply --source-dir path/to/source-pack --areas frontend administration_tool
```

Default behaviour is **plan-first**. `apply` only rewrites area base templates and writes `_templatify/shell.html` files for the chosen areas.
