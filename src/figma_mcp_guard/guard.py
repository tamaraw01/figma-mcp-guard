"""Safety checks for token replace diffs and hardcoded literal values in source files."""

from __future__ import annotations

import re
from pathlib import Path

from .check import var_name
from .tokens import Finding, Token, load_tokens, normalize

HEX_LIT = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
PX_LIT = re.compile(r"(?<![A-Za-z0-9_.-])(\d+(?:\.\d+)?px)\b")
VAR_FALLBACK = re.compile(r"var\(\s*--[A-Za-z0-9_-]+\s*,[^)]*\)")
CSS_DECL_HEAD = re.compile(r"^\s*--[A-Za-z0-9_-]+\s*:")


def check_replace_diff(old_path: Path, new_path: Path, max_delete_ratio: float = 0.5) -> list[Finding]:
    old_tok, err1 = load_tokens([old_path])
    new_tok, err2 = load_tokens([new_path])
    if err1 or err2:
        return [f for f in err1 + err2 if f.rule == "FMG000"]
    if not new_tok:
        return [Finding("FMG009", "error", "incoming token set is empty; refusing replace diff", str(new_path))]
    removed = sorted(set(old_tok) - set(new_tok))
    if old_tok and (len(removed) / len(old_tok)) > max_delete_ratio:
        pct = round(100 * len(removed) / len(old_tok))
        return [Finding("FMG010", "error",
                        f"replace diff deletes {len(removed)}/{len(old_tok)} tokens ({pct}%), "
                        f"above {round(100 * max_delete_ratio)}% limit", str(new_path))]
    return []


def scan_literals(tokens: dict[str, Token], paths: list[Path], prefix: str | None = None) -> list[Finding]:
    by_val: dict[str, list[str]] = {}
    for tok in sorted(tokens.values(), key=lambda t: t.path):
        if tok.value and not tok.alias_of:
            by_val.setdefault(tok.value, []).append(var_name(tok.path, prefix))
    # Fallback to aliases too if a value only exists via alias.
    for tok in sorted(tokens.values(), key=lambda t: t.path):
        if tok.value and tok.value not in by_val:
            by_val.setdefault(tok.value, []).append(var_name(tok.path, prefix))

    findings: list[Finding] = []
    for path in paths:
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(lines, 1):
            if CSS_DECL_HEAD.match(line):
                continue
            cleaned = VAR_FALLBACK.sub("", line)
            for rx, rule, kind in ((HEX_LIT, "FMG011", "hex color"), (PX_LIT, "FMG012", "px value")):
                for m in rx.finditer(cleaned):
                    norm = normalize(m.group(0))
                    if norm in by_val:
                        suggestions = ", ".join(by_val[norm][:3])
                        findings.append(Finding(
                            rule, "warning",
                            f"hardcoded {kind} '{m.group(0)}' matches {suggestions}",
                            str(path), lineno))
    return findings
