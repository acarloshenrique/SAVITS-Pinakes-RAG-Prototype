from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

HEALTH_REPORT_PATH = Path("reports/source_validation_report.json")
HEALTH_HISTORY_PATH = Path("reports/source_health_history.jsonl")
PRIMARY_SOURCES = ("openalex", "oasisbr", "bdtd")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_load(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def summarize_source_health(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_source: Dict[str, Dict[str, Any]] = {}
    remote_ready = 0
    fallback_only = 0
    for row in rows:
        source = str(row.get("source") or "").strip().lower()
        if not source:
            continue
        mode = str(row.get("mode") or "")
        ok = bool(row.get("ok"))
        is_remote = bool(row.get("remote_ok")) or mode in {"remote", "cache"}
        is_fallback = mode == "fallback"
        by_source[source] = {
            "ok": ok,
            "mode": mode,
            "count": int(row.get("count") or 0),
            "remote_ok": is_remote and ok,
            "fallback_only": is_fallback and ok,
            "elapsed_seconds": float(row.get("elapsed_seconds") or 0.0),
        }
        if by_source[source]["remote_ok"]:
            remote_ready += 1
        if by_source[source]["fallback_only"]:
            fallback_only += 1

    primary_remote_ready = sum(
        1 for source in PRIMARY_SOURCES if by_source.get(source, {}).get("remote_ok")
    )
    return {
        "generated_at": _now_iso(),
        "sources": by_source,
        "total_sources": len(by_source),
        "remote_ready_sources": remote_ready,
        "fallback_only_sources": fallback_only,
        "primary_remote_ready": primary_remote_ready,
        "primary_required": len(PRIMARY_SOURCES),
        "healthy": primary_remote_ready >= 2,
    }


def read_source_health(report_path: Path = HEALTH_REPORT_PATH) -> Dict[str, Any]:
    rows = _safe_load(report_path)
    return summarize_source_health(rows)


def append_health_history(
    summary: Dict[str, Any],
    output_path: Path = HEALTH_HISTORY_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
