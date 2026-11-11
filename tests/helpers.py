import json
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def write(dir_path: Path, name: str, content) -> Path:
    path = dir_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return path


TOKENS = {
    "color": {
        "$type": "color",
        "base": {"blue": {"$value": "#1D4ED8"}, "gray": {"$value": "#F3F4F6"}},
        "brand": {"primary": {"$value": "{color.base.blue}"}},
    },
    "radius": {"md": {"$type": "dimension", "$value": {"value": 12, "unit": "px"}}},
    "font": {"weight": {"bold": {"$type": "fontWeight", "$value": 700}}},
    "gradient": {"hero": {"$type": "gradient", "$value": [
        {"color": "#000000", "position": 0}, {"color": "#ffffff", "position": 1}]}},
}

CLEAN_CSS = """/* generated */
@theme {
  --color-base-blue: #1d4ed8;
  --color-base-gray: #f3f4f6;
  --color-brand-primary: var(--color-base-blue);
  --radius-md: 12px;
  --font-weight-bold: 700;
}
.dark { --color-base-gray: #111827; }
"""
