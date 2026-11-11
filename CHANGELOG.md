# Changelog

## 1.0.0 (2026-11-11)

- Initial release of `figma-mcp-guard` (MIT, Python 3.10+ stdlib only).
- Added `check` subcommand for DTCG token vs `:root` / `html` / Tailwind v4 `@theme` diffing (`FMG001` to `FMG008`).
- Added `diff-guard` subcommand to block empty or mass-deleting token replace diffs (`FMG009`, `FMG010`).
- Added `scan` subcommand to flag raw hex and `px` literals when a token exists (`FMG011`, `FMG012`).
- Added `doctor` subcommand and unit test suite.
