from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_template(filename: str, context: dict[str, Any]) -> str:
    path = TEMPLATE_DIR / filename
    if not path.is_file():
        return "<h1>Template missing</h1>"
    content = path.read_text(encoding="utf-8")
    template = Template(content)
    normalized = {key: "" if value is None else value for key, value in context.items()}
    return template.safe_substitute(normalized)
