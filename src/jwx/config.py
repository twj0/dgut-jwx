from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import jsonc


DEFAULT_BASE_URL = "https://jwx.dgut.edu.cn"
DEFAULT_COOKIE_NAMES = ("bzb_jsxsd",)


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def _parse_cookie_data(data: Any) -> str | None:
    if isinstance(data, str):
        value = data.strip()
        return value or None

    if isinstance(data, dict):
        for name in DEFAULT_COOKIE_NAMES:
            if name in data and isinstance(data[name], str) and data[name].strip():
                return data[name].strip()
        return None

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            if name in DEFAULT_COOKIE_NAMES and isinstance(value, str) and value.strip():
                return value.strip()
        return None

    return None


def load_cookie_value(cookie_file: str | None) -> str:
    env_cookie = os.getenv("JWX_COOKIE")
    if env_cookie and env_cookie.strip():
        return env_cookie.strip()

    if cookie_file:
        path = Path(cookie_file)
    else:
        path = _first_existing(
            [
                Path("cookie.jsonc"),
                Path("cookie.json"),
                Path("cookie.jsonl"),
                Path("cookie.txt"),
            ]
        )
        if path is None:
            raise FileNotFoundError(
                "Missing cookie. Provide --cookie/--cookie-file or set JWX_COOKIE."
            )

    suffix = path.suffix.lower()
    if suffix in (".txt",):
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise ValueError(f"Empty cookie file: {path}")
        return value

    if suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            value = _parse_cookie_data(data)
            if value:
                return value
        raise ValueError(f"Cookie not found in jsonl: {path}")

    data = jsonc.load(path)
    value = _parse_cookie_data(data)
    if not value:
        raise ValueError(f"Cookie not found in: {path}")
    return value


@dataclass(frozen=True)
class JwxRuntime:
    base_url: str = DEFAULT_BASE_URL
    cookie_value: str = ""
    batch_id: str | None = None
    isallsc: str = ""
    timeout_s: float = 15.0

