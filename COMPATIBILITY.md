# Compatibility matrix

| Surface | Supported | Notes |
|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | Standard library only; zero external runtime packages |
| OS | Linux, macOS, Windows | Uses `pathlib` and `python3 -m figma_mcp_guard` |
| Token formats | W3C DTCG JSON (`$value`, `$type`, `{alias.path}`) | Handles color strings, color objects with `hex`, `{value, unit}` dimensions, numbers, gradients/composites |
| CSS outputs | `:root`, `html`, Tailwind v4 `@theme` | Follows `var(--token)` chains and reports line numbers on drift |
| Source scan targets | `.css`, `.scss`, `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.svelte`, `.html` | Flags raw hex and `px` literals when a matching token exists |
| MCP clients | Claude Code, Cursor, Windsurf, Codex, Copilot | Runs as a plain CLI or CI step; no client-specific plugin required |
