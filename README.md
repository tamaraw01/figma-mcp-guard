# figma-mcp-guard

Zero-dependency CLI that checks W3C DTCG design tokens against generated CSS custom properties and Tailwind v4 `@theme` blocks.

Design-to-code MCP runs often drop variables, hardcode raw hex or pixel values, flatten alias chains into literals, or overwrite a full token file with a partial export. `figma-mcp-guard` catches those issues before merge using only the Python standard library.

## Quick start (1 command)

```bash
bash scripts/check.sh
```

Or run directly from the archive root without installing packages:

```bash
PYTHONPATH=src python3 -m figma_mcp_guard doctor
PYTHONPATH=src python3 -m figma_mcp_guard check --tokens examples/tokens.json --css examples/theme.css
```

Install into a virtualenv if you want the `figma-mcp-guard` command on your `PATH`:

```bash
python3 -m pip install . --no-build-isolation
```

## Subcommands

- `check --tokens <json...> --css <css...> [--scan <src...>] [--prefix <name>] [--strict] [--format text|json]`
  Compare DTCG tokens against `:root`, `html`, and `@theme` CSS variables. Optionally scan source files for raw literals matching existing tokens.
- `scan --tokens <json...> --files <path...>`
  Flag raw hex colors (`FMG011`) and `px` values (`FMG012`) in code when a matching token exists.
- `diff-guard --old <prev.json> --new <next.json> [--max-delete-ratio 0.5]`
  Block empty token sets (`FMG009`) or replace diffs that delete more than the configured fraction of tokens (`FMG010`).
- `doctor`
  Verify Python version and package import health.

## Rules

| Code | Severity | Meaning |
|---|---|---|
| `FMG000` | error | Missing or unreadable token/CSS file |
| `FMG001` | error | Token has no matching CSS variable |
| `FMG002` | error | CSS variable value differs from resolved DTCG token |
| `FMG003` | warning | CSS variable inside a token group has no backing token (shows rename hint when values match) |
| `FMG004` | error | Non-scalar string written into CSS (`[object Object]`, `undefined`, `NaN`, `null`) |
| `FMG005` | warning | Alias token written as a literal instead of `var(--...)` |
| `FMG006` | error | Unresolved `{alias.path}` target |
| `FMG007` | error | Circular alias chain |
| `FMG008` | error | Same token path defined with conflicting values across token files |
| `FMG009` | error | Incoming token set is empty in `diff-guard` |
| `FMG010` | error | Replace diff exceeds `--max-delete-ratio` |
| `FMG011` | warning | Hardcoded hex color in code matches an existing token |
| `FMG012` | warning | Hardcoded `px` value in code matches an existing token |

## How tokens map to CSS variables

Each segment of the token path is lowercased, camelCase is split with a hyphen, and the segments are joined with `-` under a `--` prefix. `--prefix` adds one more leading segment.

| Token path | `--prefix` | CSS variable |
|---|---|---|
| `color.brand.primary` | none | `--color-brand-primary` |
| `color.brand.primary` | `ds` | `--ds-color-brand-primary` |
| `fontSize.bodyLg` | none | `--font-size-body-lg` |

Only declarations inside `:root`, `html`, or `@theme` count as base values. `FMG003` looks at base variables whose name starts with the group of an existing token (for example `--color-`), so unrelated variables are left alone.

When a directory is passed, `--css` reads only `.css` files, and `--scan` / `scan --files` read only `.css`, `.scss`, `.ts`, `.tsx`, `.js`, `.jsx`, `.vue`, `.svelte`, and `.html` files.

## Exit codes

- `0`: no errors, and no warnings when `--strict` is set
- `1`: at least one error, or at least one warning under `--strict`. A missing token or CSS file is reported as `FMG000` and also exits `1`.
- `2`: invalid arguments (reported by `argparse`)

## Current limits

- Mode and component overrides such as `.dark { ... }` or `[data-theme] { ... }` are parsed but not compared with tokens.
- An alias is resolved only when it is the whole value (`"{color.base.blue}"`). Aliases inside longer strings, such as `"{size.border} solid"`, stay unresolved.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

License: MIT (`LICENSE`). See `COMPATIBILITY.md` for supported Python versions and formats.
