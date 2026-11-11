"""Compare resolved DTCG tokens with CSS custom properties from :root, html, or Tailwind v4 @theme."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .tokens import Finding, Token, normalize

DECL = re.compile(r"^\s*(--[A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", re.S)
VAR_REF = re.compile(r"^var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,[^)]*)?\)$")
BROKEN = ("[object object]", "undefined", "nan", "null")
BASE_SELECTORS = (":root", "html")


@dataclass
class Decl:
    name: str
    value: str
    file: str
    line: int
    base: bool  # True when declared in :root, html, or @theme (not a mode or component override)


def var_name(token_path: str, prefix: str | None = None) -> str:
    parts = [prefix] if prefix else []
    for seg in token_path.split("."):
        seg = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", seg)
        parts.append(re.sub(r"[^a-z0-9]+", "-", seg.lower()).strip("-"))
    return "--" + "-".join(p for p in parts if p)


def _strip_comments(text: str) -> str:
    # Keep newlines so reported line numbers stay accurate.
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def parse_css(path: Path) -> list[Decl]:
    text = _strip_comments(Path(path).read_text(encoding="utf-8"))
    decls: list[Decl] = []
    stack: list[str] = []
    start = 0
    for i, ch in enumerate(text + ";"):
        if ch not in "{};":
            continue
        chunk = text[start:i]
        if ch == "{":
            stack.append(" ".join(chunk.split()))
        else:
            m = DECL.match(chunk)
            if m and stack:
                lead = len(chunk) - len(chunk.lstrip())
                line = text.count("\n", 0, start + lead) + 1
                prelude = stack[-1]
                base = prelude.startswith("@theme") or prelude in BASE_SELECTORS
                decls.append(Decl(m.group(1), " ".join(m.group(2).split()), str(path), line, base))
            if ch == "}" and stack:
                stack.pop()
        start = i + 1
    return decls


def _follow(value: str, base: dict[str, Decl]) -> str:
    for _ in range(16):
        m = VAR_REF.match(value)
        if not m or m.group(1) not in base:
            return value
        value = base[m.group(1)].value
    return value


def check(tokens: dict[str, Token], css_paths: list[Path], prefix: str | None = None) -> list[Finding]:
    base: dict[str, Decl] = {}
    for path in css_paths:
        for d in parse_css(path):
            if d.base:
                base[d.name] = d
    # ponytail: mode overrides (.dark, [data-theme]) are parsed but not compared. Add with per-mode token files.
    findings: list[Finding] = []
    expected: dict[str, Token] = {}
    for tok in sorted(tokens.values(), key=lambda t: t.path):
        name = var_name(tok.path, prefix)
        d = base.get(name)
        if tok.value is None:  # composite token: only catch serialization bugs
            if d and any(b in d.value.lower() for b in BROKEN):
                findings.append(Finding("FMG004", "error", f"{name} holds a non-scalar value '{d.value}'", d.file, d.line))
            continue
        expected[name] = tok
        if d is None:
            findings.append(Finding("FMG001", "error", f"token '{tok.path}' has no CSS variable {name}"))
            continue
        low = d.value.lower()
        if any(low == b or b in low for b in BROKEN if b == "[object object]") or low in BROKEN:
            findings.append(Finding("FMG004", "error", f"{name} holds a non-scalar value '{d.value}'", d.file, d.line))
            continue
        got = normalize(_follow(d.value, base))
        if got != tok.value:
            findings.append(Finding("FMG002", "error",
                                    f"{name} is '{d.value}' but token '{tok.path}' is '{tok.value}'", d.file, d.line))
        elif tok.alias_of and not VAR_REF.match(d.value):
            findings.append(Finding("FMG005", "warning",
                                    f"{name} is a literal, but token '{tok.path}' aliases '{tok.alias_of}'. "
                                    f"Use var({var_name(tok.alias_of, prefix)}) so theme changes propagate", d.file, d.line))
    groups = {var_name(t.path.split(".")[0], prefix) + "-" for t in tokens.values()}
    missing = {n: t for n, t in expected.items() if n not in base}
    for name, d in sorted(base.items()):
        if name in expected or not any(name.startswith(g) for g in groups):
            continue
        got = normalize(_follow(d.value, base))
        twins = [t.path for t in missing.values() if t.value == got]
        hint = f", possibly renamed from token '{twins[0]}'" if twins else ""
        findings.append(Finding("FMG003", "warning", f"{name} is not backed by any token{hint}", d.file, d.line))
    return findings
