from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_retrieval_event(
    query: str,
    top_k: int,
    diagnostics: Dict[str, object],
    output_path: str = "reports/slo_events.jsonl",
) -> None:
    row = {
        "timestamp": _now_iso(),
        "query": query[:250],
        "top_k": top_k,
        "total_docs": diagnostics.get("total", 0),
        "remote_api_docs": diagnostics.get("remote_api_docs", 0),
        "fallback_api_docs": diagnostics.get("fallback_api_docs", 0),
        "per_source": diagnostics.get("per_source", {}),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
