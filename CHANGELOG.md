# Changelog

All notable changes to this project are documented in this file.

## [v1.0.0] - 2026-04-09

### Added

- Release-ready README assets with a demo screenshot and architecture diagram.
- A reproducible offline benchmark in `src/evaluation/simple_benchmark.py`.
- Generated benchmark reports in `reports/benchmark_v1.0.0.json` and `reports/benchmark_v1.0.0.md`.
- `ROADMAP.md` and this changelog for release management.
- Tests covering ingestion cache utilities and offline pipeline behavior.

### Changed

- Updated the README to explain architecture, business impact, and benchmark results.
- Enabled `pinned: true` in the Space front matter so the project can be pinned on the profile once published.
- Prioritized domain-specific sources during offline deduplication so BrCris and BDTD records are retained ahead of OpenAlex fallback when duplicates exist.
- Replaced non-ASCII console markers in `src/semantic_integration.py` with ASCII-safe logs for Windows compatibility.

### Fixed

- Restored `src/ingestion/source_client.py`, which was missing and breaking `python build_graph.py`.
- Fixed offline graph generation and added test coverage to prevent the release pipeline from regressing silently.
