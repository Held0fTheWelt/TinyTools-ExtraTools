# mvpify

`mvpify` imports prepared MVP bundles into the governed fy workspace.

It normalizes imported content under `mvpify/imports/<id>/normalized` and mirrors imported MVP documentation into `docs/MVPs/imports/<id>` so temporary implementation folders can later be removed without losing the documentation trail.

It also coordinates the surrounding suite family:
- `contractify` for contracts and ADR governance
- `despaghettify` for insertion-path discipline
- `testify` for verification
- `documentify` / `docify` / `templatify` / `usabilify` / `securify` for follow-up quality work
- `observifyfy` for internal cross-suite tracking
