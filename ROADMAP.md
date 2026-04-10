# Roadmap

## v1.0.x Hardening

- Keep the release benchmark current for every tagged version.
- Add a GIF capture workflow so the README hero can switch from static screenshot to short product demo.
- Add CI checks for `python build_graph.py`, benchmark generation, and README asset integrity.

## v1.1 Retrieval Quality

- Add query relevance labels for a larger evaluation set built from `docs/chat_eval_prompts.md`.
- Introduce reranking or scoring improvements for governance-heavy queries.
- Expose retrieval traces in the UI so users can inspect why a result was returned.

## v1.2 Data and Governance Coverage

- Expand real connector support for BrCris, Oasisbr, and BDTD with stronger schema adapters.
- Persist connector samples and cache metadata for easier debugging and reproducibility.
- Add more granular governance indicators for provenance gaps, license completeness, and DEIA coverage.

## v2.0 Pilot Readiness

- Add API endpoints for institutional integration beyond the Streamlit demo.
- Add authentication, usage analytics, and basic observability for pilot deployments.
- Support larger corpora, background refresh jobs, and release automation tied to benchmark thresholds.
