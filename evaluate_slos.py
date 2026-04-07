from __future__ import annotations

from src.analytics.slo_evaluator import build_slo_report


def main() -> int:
    report = build_slo_report()
    metrics = report.get("metrics", {})
    print("SLO evaluation")
    print(f"- pass={report.get('pass')} events={report.get('events_analyzed', 0)}")
    print(f"- availability={metrics.get('availability_ratio', 0.0)}")
    print(f"- latency_p95_seconds={metrics.get('latency_p95_seconds', 0.0)}")
    print(
        f"- remote_docs_ratio(>={metrics.get('remote_docs_min_n', 0)} docs)="
        f"{metrics.get('remote_docs_ratio', 0.0)}"
    )
    print(f"- fallback_ratio_by_source={metrics.get('fallback_ratio_by_source', {})}")
    print("Report: reports/slo_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
