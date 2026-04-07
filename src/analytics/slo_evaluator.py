from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

EVENTS_PATH = Path("reports/slo_events.jsonl")
REPORT_PATH = Path("reports/slo_report.json")


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class SLOTargets:
    availability_min: float = 0.99
    latency_p95_max_seconds: float = 6.0
    remote_docs_min_n: int = 2
    remote_docs_ratio_min: float = 0.9
    fallback_ratio_max_default: float = 0.2

    def fallback_ratio_limits(self, sources: List[str]) -> Dict[str, float]:
        limits: Dict[str, float] = {}
        for source in sources:
            key = f"SLO_FALLBACK_MAX_{source.upper()}"
            limits[source] = _float_env(key, self.fallback_ratio_max_default)
        return limits


def load_targets() -> SLOTargets:
    return SLOTargets(
        availability_min=_float_env("SLO_AVAILABILITY_MIN", 0.99),
        latency_p95_max_seconds=_float_env("SLO_LATENCY_P95_MAX_SECONDS", 6.0),
        remote_docs_min_n=_int_env("SLO_REMOTE_DOCS_MIN_N", 2),
        remote_docs_ratio_min=_float_env("SLO_REMOTE_DOCS_RATIO_MIN", 0.9),
        fallback_ratio_max_default=_float_env("SLO_FALLBACK_MAX_DEFAULT", 0.2),
    )


def read_events(path: Path = EVENTS_PATH) -> List[Dict]:
    if not path.exists():
        return []
    rows: List[Dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = percentile * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def compute_metrics(events: List[Dict], targets: SLOTargets) -> Dict:
    total = len(events)
    if total == 0:
        return {
            "total_requests": 0,
            "availability_ratio": 0.0,
            "latency_p95_seconds": 0.0,
            "remote_docs_ratio": 0.0,
            "remote_docs_min_n": targets.remote_docs_min_n,
            "fallback_ratio_by_source": {},
        }

    available = 0
    remote_docs_ok = 0
    latencies: List[float] = []
    fallback_counts: Dict[str, int] = {}
    source_counts: Dict[str, int] = {}

    for event in events:
        blocked = bool(event.get("blocked_by_reliability_gate"))
        total_docs = int(event.get("total_docs") or 0)
        if (not blocked) and total_docs > 0:
            available += 1

        remote_docs = int(event.get("remote_api_docs") or 0)
        if remote_docs >= targets.remote_docs_min_n:
            remote_docs_ok += 1

        latencies.append(float(event.get("retrieval_elapsed_seconds") or 0.0))

        per_source = event.get("per_source") or {}
        if isinstance(per_source, dict):
            for source, mode_counts in per_source.items():
                if not isinstance(mode_counts, dict):
                    continue
                total_source = 0
                fallback_source = 0
                for mode, count in mode_counts.items():
                    num = int(count or 0)
                    total_source += num
                    if str(mode) == "fallback":
                        fallback_source += num
                source_counts[source] = source_counts.get(source, 0) + total_source
                fallback_counts[source] = fallback_counts.get(source, 0) + fallback_source

    fallback_ratio_by_source: Dict[str, float] = {}
    for source, total_source in source_counts.items():
        if total_source <= 0:
            continue
        fallback_ratio_by_source[source] = round(
            fallback_counts.get(source, 0) / total_source, 4
        )

    return {
        "total_requests": total,
        "availability_ratio": round(available / total, 4),
        "latency_p95_seconds": round(_percentile(latencies, 0.95), 4),
        "remote_docs_ratio": round(remote_docs_ok / total, 4),
        "remote_docs_min_n": targets.remote_docs_min_n,
        "fallback_ratio_by_source": fallback_ratio_by_source,
    }


def evaluate_metrics(metrics: Dict, targets: SLOTargets) -> Dict:
    fallback_limits = targets.fallback_ratio_limits(
        list((metrics.get("fallback_ratio_by_source") or {}).keys())
    )
    checks = {
        "availability": {
            "actual": metrics.get("availability_ratio", 0.0),
            "target_min": targets.availability_min,
            "pass": metrics.get("availability_ratio", 0.0) >= targets.availability_min,
        },
        "latency_p95": {
            "actual_seconds": metrics.get("latency_p95_seconds", 0.0),
            "target_max_seconds": targets.latency_p95_max_seconds,
            "pass": metrics.get("latency_p95_seconds", 0.0) <= targets.latency_p95_max_seconds,
        },
        "remote_docs_ratio": {
            "actual": metrics.get("remote_docs_ratio", 0.0),
            "target_min": targets.remote_docs_ratio_min,
            "remote_docs_min_n": targets.remote_docs_min_n,
            "pass": metrics.get("remote_docs_ratio", 0.0) >= targets.remote_docs_ratio_min,
        },
        "fallback_ratio_by_source": {},
    }

    fallback_actual = metrics.get("fallback_ratio_by_source") or {}
    fallback_pass = True
    for source, ratio in fallback_actual.items():
        limit = fallback_limits.get(source, targets.fallback_ratio_max_default)
        source_ok = float(ratio) <= limit
        checks["fallback_ratio_by_source"][source] = {
            "actual": ratio,
            "target_max": limit,
            "pass": source_ok,
        }
        fallback_pass = fallback_pass and source_ok

    overall_pass = (
        checks["availability"]["pass"]
        and checks["latency_p95"]["pass"]
        and checks["remote_docs_ratio"]["pass"]
        and fallback_pass
    )
    return {
        "targets": asdict(targets),
        "metrics": metrics,
        "checks": checks,
        "pass": overall_pass,
    }


def build_slo_report(events_path: Path = EVENTS_PATH, report_path: Path = REPORT_PATH) -> Dict:
    targets = load_targets()
    events = read_events(events_path)
    metrics = compute_metrics(events, targets)
    report = evaluate_metrics(metrics, targets)
    report["events_analyzed"] = len(events)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
