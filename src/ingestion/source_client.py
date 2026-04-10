from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, List

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT_DIR / "data" / "cache"
SAMPLE_DIR = ROOT_DIR / "reports" / "source_samples"
DEFAULT_TIMEOUT = int(os.environ.get("SAVITS_SOURCE_TIMEOUT", "20"))
DEFAULT_CACHE_TTL_HOURS = int(os.environ.get("SAVITS_CACHE_TTL_HOURS", "24"))
DEFAULT_MAX_PAGES = int(os.environ.get("SAVITS_MAX_SOURCE_PAGES", "2"))


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "no", "off", "false"}


def should_use_cache_first() -> bool:
    return not _bool_env("SAVITS_USE_REMOTE_SOURCES", default=False)


def max_pages() -> int:
    return max(1, DEFAULT_MAX_PAGES)


def _cache_path(source: str) -> Path:
    return CACHE_DIR / f"{source}.json"


def _sample_path(source: str) -> Path:
    return SAMPLE_DIR / f"{source}.json"


def _is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_limit = timedelta(hours=DEFAULT_CACHE_TTL_HOURS)
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return datetime.now(timezone.utc) - modified <= age_limit


def _read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def request_json(source: str, url: str, params: dict | None = None, headers: dict | None = None) -> Any:
    merged_headers = {"Accept": "application/json", "User-Agent": f"savits-pinakes/{source}"}
    if headers:
        merged_headers.update(headers)
    response = requests.get(url, params=params, headers=merged_headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def extract_records(payload: Any, keys: Iterable[str]) -> list[Any]:
    stack = [payload]
    while stack:
        current = stack.pop(0)
        if isinstance(current, list):
            if current and isinstance(current[0], dict):
                return current
            continue
        if not isinstance(current, dict):
            continue

        for key in keys:
            value = current.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                stack.append(value)

        for value in current.values():
            if isinstance(value, (dict, list)):
                stack.append(value)
    if isinstance(payload, list):
        return payload
    return []


def _normalize_cache_payload(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return records
    if isinstance(payload, list):
        return payload
    return []


def load_cache(source: str, limit: int | None = None, allow_stale: bool = False) -> list[dict]:
    path = _cache_path(source)
    if not path.exists():
        return []
    if not allow_stale and not _is_fresh(path):
        return []

    records = _normalize_cache_payload(_read_json(path))
    if limit:
        return records[:limit]
    return records


def _dedup_key(item: dict, keys: Iterable[str]) -> str:
    for key in keys:
        value = item.get(key)
        if value:
            return f"{key}:{str(value).strip().lower()}"
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def unique_by(items: Iterable[dict], *keys: str) -> list[dict]:
    seen: set[str] = set()
    unique_items: List[dict] = []
    for item in items:
        dedup_key = _dedup_key(item, keys)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        unique_items.append(item)
    return unique_items


def write_cache(source: str, records: list[dict], origin: str = "remote") -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source,
        "origin": origin,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": records,
    }
    with open(_cache_path(source), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def write_sample(source: str, payload: Any) -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_sample_path(source), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
