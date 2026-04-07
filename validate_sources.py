from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.ingestion.bdtd_harvester import harvest_bdtd
from src.ingestion.brcris_harvester import harvest_brcris
from src.ingestion.oasisbr_harvester import harvest_oasisbr
from src.ingestion.openalex_harvester import harvest_openalex
from src.ingestion.source_client import cache_path, sample_path


def _source_mode(records: List[Dict[str, Any]]) -> str:
    if not records:
        return "empty"
    mode = str(records[0].get("ingestion_mode") or "").strip()
    if mode:
        return mode
    source_uri = str(records[0].get("source_uri") or "")
    if source_uri.startswith("internal://"):
        return "fallback"
    return "remote"


def _run(source: str, fetch_fn: Callable[[], List[Dict[str, Any]]]) -> Dict[str, Any]:
    status: Dict[str, Any] = {"source": source}
    try:
        records = fetch_fn()
        status["ok"] = bool(records)
        status["count"] = len(records)
        status["mode"] = _source_mode(records)
    except Exception as exc:
        status["ok"] = False
        status["count"] = 0
        status["mode"] = "error"
        status["error"] = str(exc)

    cache_file = cache_path(source)
    sample_file = sample_path(source)
    status["cache"] = str(cache_file) if cache_file.exists() else None
    status["sample"] = str(sample_file) if sample_file.exists() else None
    return status


def main() -> int:
    checks = [
        ("openalex", lambda: harvest_openalex(per_page=30, force_refresh=True)),
        ("brcris", lambda: harvest_brcris(limit=30, force_refresh=True)),
        ("oasisbr", lambda: harvest_oasisbr(limit=30, force_refresh=True)),
        ("bdtd", lambda: harvest_bdtd(limit=30, force_refresh=True)),
    ]
    results = [_run(source, fn) for source, fn in checks]

    report_path = Path("reports/source_validation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Source validation finished")
    print(f"Report: {report_path}")
    for row in results:
        print(
            f"- {row['source']}: ok={row['ok']} mode={row['mode']} count={row['count']} "
            f"cache={bool(row['cache'])} sample={bool(row['sample'])}"
        )
        if row.get("error"):
            print(f"  error: {row['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
