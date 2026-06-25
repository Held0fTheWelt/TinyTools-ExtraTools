# Wave 1 Compatibility Baseline

This document captures the operational compatibility surface before Wave 1 platform extraction.

## Coverage

- CLI commands and subcommands (`--help` surfaces)
- Exit code behavior categories
- Default filenames and directory structures
- Stable JSON key surfaces consumed by automation

## Notes

- This baseline is intentionally additive: migration slices must preserve legacy behavior unless explicitly deprecated.
- Any compatibility break must be represented in a deprecation matrix before release.
