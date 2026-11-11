"""Load W3C DTCG token files into a flat, alias-resolved map."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ALIAS = re.compile(r"^\{([^{}]+)\}$")
HEX = re.compile(r"^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$")


@dataclass
class Finding:
    rule: str
    severity: str  # "error" or "warning"
    message: str
    file: str = ""
    line: int = 0


@dataclass
class Token:
    path: str
    type: str | None
    raw: object
    source: str
    value: str | None = None  # normalized scalar, None for composites
    alias_of: str | None = None


def _num(v) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def normalize(value) -> str | None:
    """Return a comparable scalar string, or None when the value has no single CSS form."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _num(value)
    if isinstance(value, dict):
        if "hex" in value:
            return normalize(value["hex"])
        if "value" in value and "unit" in value and isinstance(value["value"], (int, float)):
            return _num(value["value"]) + str(value["unit"])
        return None
    if not isinstance(value, str):
        return None
    s = re.sub(r"\s+", " ", value.strip().lower())
    s = re.sub(r"\s*,\s*", ", ", s)
    m = HEX.match(s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8 and h.endswith("ff"):
            h = h[:6]
        s = "#" + h
    return s


def _walk(node: dict, prefix: str, inherited: str | None, source: str, out: list[Token]) -> None:
    group_type = node.get("$type", inherited)
    for key, child in node.items():
        if key.startswith("$") or not isinstance(child, dict):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if "$value" in child:
            out.append(Token(path, child.get("$type", group_type), child["$value"], source))
        else:
            _walk(child, path, group_type, source, out)


def _alias_target(raw) -> str | None:
    m = ALIAS.match(raw.strip()) if isinstance(raw, str) else None
    return m.group(1) if m else None


def _comparable(raw):
    n = normalize(raw)
    return n if n is not None else json.dumps(raw, sort_keys=True)


def load_tokens(paths: list[Path]) -> tuple[dict[str, Token], list[Finding]]:
    findings: list[Finding] = []
    tokens: dict[str, Token] = {}
    for path in paths:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(Finding("FMG000", "error", f"cannot read token file: {exc}", str(path)))
            continue
        if not isinstance(data, dict):
            findings.append(Finding("FMG000", "error", "token file root must be a JSON object", str(path)))
            continue
        found: list[Token] = []
        _walk(data, "", None, str(path), found)
        for tok in found:
            prev = tokens.get(tok.path)
            if prev is None:
                tokens[tok.path] = tok
            elif _comparable(prev.raw) != _comparable(tok.raw):
                findings.append(Finding(
                    "FMG008", "error",
                    f"token '{tok.path}' has different values in {Path(prev.source).name} "
                    f"({prev.raw!r}) and {Path(tok.source).name} ({tok.raw!r}), so aliases to it are ambiguous",
                    str(path)))
    for tok in tokens.values():
        _resolve(tok, tokens, findings)
    return tokens, findings


def _resolve(tok: Token, tokens: dict[str, Token], findings: list[Finding]) -> None:
    seen = [tok.path]
    raw = tok.raw
    target = _alias_target(raw)
    tok.alias_of = target
    while target is not None:
        if target in seen:
            findings.append(Finding("FMG007", "error",
                                    f"circular alias: {' -> '.join(seen + [target])}", tok.source))
            return
        ref = tokens.get(target)
        if ref is None:
            findings.append(Finding("FMG006", "error",
                                    f"token '{tok.path}' points to missing token '{{{target}}}'", tok.source))
            return
        seen.append(target)
        if tok.type is None:
            tok.type = ref.type
        raw = ref.raw
        target = _alias_target(raw)
    # ponytail: aliases inside longer strings ("{a} solid") stay unresolved. Add when a real token file needs it.
    tok.value = normalize(raw)
