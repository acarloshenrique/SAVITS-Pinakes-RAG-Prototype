from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.5
DEFAULT_CACHE_TTL_HOURS = 24
DEFAULT_MAX_PAGES = 10


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid integer for %s=%r, using %s", name, raw, default)
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r, using %s", name, raw, default)
        return default


def cache_root() -> Path:
    return Path(os.environ.get("INGESTION_CACHE_DIR", "data/cache/ingestion"))


def samples_root() -> Path:
    return Path(os.environ.get("INGESTION_SAMPLES_DIR", "reports/ingestion_samples"))


def cache_path(source: str) -> Path:
    return cache_root() / f"{source}.json"


def sample_path(source: str) -> Path:
    return samples_root() / f"{source}_sample.json"


def should_use_cache_first() -> bool:
    return _bool_env("INGESTION_USE_CACHE_FIRST", True)


def max_pages() -> int:
    return max(1, _int_env("INGESTION_MAX_PAGES", DEFAULT_MAX_PAGES))


def cache_ttl_hours() -> int:
    return max(1, _int_env("INGESTION_CACHE_TTL_HOURS", DEFAULT_CACHE_TTL_HOURS))


def retries() -> int:
    return max(1, _int_env("INGESTION_RETRIES", DEFAULT_RETRIES))


def timeout_seconds() -> float:
    return max(1.0, _float_env("INGESTION_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))


def backoff_seconds() -> float:
    return max(0.1, _float_env("INGESTION_BACKOFF_SECONDS", DEFAULT_BACKOFF_SECONDS))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slice_limit(records: List[Dict[str, Any]], limit: int | None) -> List[Dict[str, Any]]:
    if limit is None:
        return records
    return records[:limit]


def load_cache(source: str, limit: int | None = None, allow_stale: bool = False) -> List[Dict[str, Any]] | None:
    path = cache_path(source)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse cache for %s: %s", source, exc)
        return None

    fetched_at = payload.get("fetched_at")
    records = payload.get("records")
    if not isinstance(records, list):
        return None

    if not allow_stale and fetched_at:
        try:
            fetched_ts = datetime.fromisoformat(fetched_at)
            age_seconds = (datetime.now(timezone.utc) - fetched_ts).total_seconds()
            if age_seconds > cache_ttl_hours() * 3600:
                return None
        except Exception:
            logger.warning("Ignoring invalid timestamp in cache for %s", source)

    limited = _slice_limit(records, limit)
    return [{**record, "ingestion_mode": "cache"} for record in limited]


def write_cache(source: str, records: List[Dict[str, Any]], origin: str = "remote") -> Path:
    path = cache_path(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source,
        "origin": origin,
        "fetched_at": _now_iso(),
        "count": len(records),
        "records": records,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_sample(source: str, payload: Any) -> Path:
    path = sample_path(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = {"source": source, "captured_at": _now_iso(), "payload": payload}
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def request_json(
    source: str,
    url: str,
    params: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
) -> Any:
    req_timeout = timeout_seconds()
    req_retries = retries()
    req_backoff = backoff_seconds()
    last_error: Exception | None = None

    for attempt in range(1, req_retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=req_timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "[%s] request failed (attempt %s/%s): %s",
                source,
                attempt,
                req_retries,
                exc,
            )
            if attempt < req_retries:
                time.sleep(req_backoff * attempt)

    raise RuntimeError(f"[{source}] remote request failed after {req_retries} attempts: {last_error}")


def extract_records(payload: Any, keys: Sequence[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    if not isinstance(payload, dict):
        return []

    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [entry for entry in value if isinstance(entry, dict)]
    return []


def unique_by(records: Iterable[Dict[str, Any]], *keys: str) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for record in records:
        key = tuple(str(record.get(name) or "") for name in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out
