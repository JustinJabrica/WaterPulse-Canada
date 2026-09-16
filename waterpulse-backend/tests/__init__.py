"""
WaterPulse Data-Source Standard (DS-STD-2026.1) — verification test suite.

Exhaustive, read-only probes of every Canadian hydrometric / weather /
environmental data source the project uses or may use, plus a gentle
residual harness for the few sources that must be scraped.

Run inside the backend container (has env + deps):
    docker-compose run --rm -w /app backend python -m tests.probe_sources
    docker-compose run --rm -w /app backend python -m tests.stress_test --smoke

Outputs land in tests/logs/<run_id>/ (bind-mounted to the host).
See tests/README.md and docs/reports/ (DS-STD-2026.1) for the standard.
"""
