from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_LINE_COMMENT_RE = re.compile(r"//.*?$", re.MULTILINE)
_BLOCK_COMMENT_RE = re.compile(r"/\\*.*?\\*/", re.DOTALL)


def loads(text: str) -> Any:
    """Parse JSON/JSONC.

    Supports // line comments and /* */ block comments (best-effort).
    """
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return json.loads(text)


def load(path: str | Path) -> Any:
    return loads(Path(path).read_text(encoding="utf-8"))

