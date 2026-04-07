from __future__ import annotations

from src.ingestion.source_health import append_health_history, read_source_health


def main() -> int:
    summary = read_source_health()
    append_health_history(summary)

    print("Source health summary")
    print(
        f"- healthy={summary['healthy']} "
        f"primary_remote_ready={summary['primary_remote_ready']}/{summary['primary_required']} "
        f"remote_ready_sources={summary['remote_ready_sources']}/{summary['total_sources']}"
    )
    for source, row in sorted(summary["sources"].items()):
        print(
            f"  - {source}: ok={row['ok']} mode={row['mode']} "
            f"remote_ok={row['remote_ok']} fallback_only={row['fallback_only']} "
            f"count={row['count']} elapsed={row['elapsed_seconds']:.3f}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
