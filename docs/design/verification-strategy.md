# Verification Strategy

Status: proposed

This document defines the system-level verification approach. Component designs add concrete cases when implementation reaches them.

## Functional verification

Functional tests cover component contracts, archive replay, the replay-to-live transition, live reconnection, schema outcomes, transformations, DuckLake writes, automatic process lifecycle, and operational health. End-to-end tests begin with captured Jetstream input and finish with analytical results and operational health.

The walking-skeleton verification traces one replayed post and one live post through the same ingestion service, raw boundary, text transformation, DuckLake persistence, and Streamlit posts table and DID counts. Textual reports the ingestion service's `replay` or `live` phase.

## Recovery verification

Recovery tests cover interrupted raw writes, persisted-cursor replay, SDK seam and reconnect deduplication, downstream duplicate handling after crashes, unavailable processing, failed DuckLake commits, Hub-lock replacement, child pipe loss, and graceful and forced shutdown.

## Supported-environment verification

Linux and WSL checks cover `platformdirs` paths, permissions, process creation, duplex-pipe communication, advisory locks, termination, and cleanup behavior.

## Performance verification

Performance tests measure sustained ingestion, transformation capacity, end-to-end lag, storage growth, cleanup behavior, and analytical query responsiveness.

The raw-retention benchmark compares JSON Lines with SQLite WAL for sustained writes, replay reads, crash recovery, cleanup, concurrent access, and settled and peak disk use. JSON Lines measurements include `.jsonl.zst` DuckDB ingestion, the 100 MiB rotation boundary, candidate batch sizes, and checkpoint synchronization policies.

## Scale verification

Development tooling replays captured Jetstream events at original or accelerated timing through the production raw-ingestion boundary. Every run uses a fresh isolated DuckLake data mart and removes it after success, failure, or interruption.

Local Markdown results remain in root-level, Git-ignored `benchmarks/`. Runs selected for publication generate reproducible Markdown summaries in `docs/benchmarks/`. Captured datasets remain outside Git. Versioned metadata records provenance and reproduction details.

Stored-data tests provide controlled scale beyond the 100 Mbps development connection. Ingestion-service tests verify protocol compatibility and network-bound end-to-end behavior.

## Open questions

- What performance targets define adequate replay and live capacity?
- What captured corpus represents each collection and important optional shape?
- Which benchmark runs form the portfolio evidence set?
