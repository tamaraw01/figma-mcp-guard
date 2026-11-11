"""CLI entrypoint for figma-mcp-guard."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .check import check
from .guard import check_replace_diff, scan_literals
from .tokens import Finding, load_tokens

CODE_EXTENSIONS = {".css", ".scss", ".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte", ".html"}


def _expand(paths: list[str], extensions: set[str] | None = None) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and (extensions is None or child.suffix.lower() in extensions):
                    out.append(child)
        elif p.exists():
            out.append(p)
        else:
            out.append(p)  # let reader emit FMG000 / missing report
    return out


def _emit(findings: list[Finding], fmt: str, strict: bool) -> int:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    if fmt == "json":
        print(json.dumps({
            "version": __version__,
            "summary": {"errors": errors, "warnings": warnings},
            "findings": [asdict(f) for f in findings],
        }, indent=2))
    else:
        for f in findings:
            loc = f"{f.file}:{f.line}: " if f.file and f.line else (f"{f.file}: " if f.file else "")
            print(f"{f.severity.upper()} {f.rule} {loc}{f.message}")
        print(f"Summary: {errors} errors, {warnings} warnings")
    return 1 if (errors > 0 or (strict and warnings > 0)) else 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="figma-mcp-guard", description="Check DTCG tokens against CSS/Tailwind @theme output.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="Check DTCG tokens against CSS custom properties / Tailwind v4 @theme")
    c.add_argument("--tokens", nargs="+", required=True, help="DTCG JSON token files")
    c.add_argument("--css", nargs="+", required=True, help="CSS files to compare against")
    c.add_argument("--scan", nargs="*", default=[], help="Optional source files/dirs to scan for raw hex/px literals")
    c.add_argument("--prefix", default=None, help="Optional CSS variable prefix (e.g. ds -> --ds-color-...)")
    c.add_argument("--strict", action="store_true", help="Exit 1 on warnings as well as errors")
    c.add_argument("--format", choices=("text", "json"), default="text")

    s = sub.add_parser("scan", help="Scan source files for hardcoded hex/px literals that match a token")
    s.add_argument("--tokens", nargs="+", required=True)
    s.add_argument("--files", nargs="+", required=True)
    s.add_argument("--prefix", default=None)
    s.add_argument("--strict", action="store_true")
    s.add_argument("--format", choices=("text", "json"), default="text")

    d = sub.add_parser("diff-guard", help="Refuse empty or mass-deleting token replace diffs")
    d.add_argument("--old", required=True, help="Previous tokens JSON")
    d.add_argument("--new", required=True, help="Incoming tokens JSON")
    d.add_argument("--max-delete-ratio", type=float, default=0.5, help="Max deleted share before failing (default 0.5)")
    d.add_argument("--strict", action="store_true")
    d.add_argument("--format", choices=("text", "json"), default="text")

    sub.add_parser("doctor", help="Verify runtime and self-check environment")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "doctor":
        print(f"figma-mcp-guard {__version__} ok (python {sys.version.split()[0]})")
        return 0
    if args.cmd == "diff-guard":
        findings = check_replace_diff(Path(args.old), Path(args.new), max_delete_ratio=args.max_delete_ratio)
        return _emit(findings, args.format, args.strict)
    tokens, findings = load_tokens(_expand(args.tokens))
    if args.cmd == "check":
        css_files = _expand(args.css, {".css"})
        for cf in css_files:
            if not cf.exists():
                findings.append(Finding("FMG000", "error", f"CSS file not found: {cf}", str(cf)))
        existing_css = [cf for cf in css_files if cf.exists()]
        if tokens or not findings:
            findings.extend(check(tokens, existing_css, prefix=args.prefix))
        if args.scan:
            findings.extend(scan_literals(tokens, _expand(args.scan, CODE_EXTENSIONS), prefix=args.prefix))
        return _emit(findings, args.format, args.strict)
    if args.cmd == "scan":
        findings.extend(scan_literals(tokens, _expand(args.files, CODE_EXTENSIONS), prefix=args.prefix))
        return _emit(findings, args.format, args.strict)
    return 2
