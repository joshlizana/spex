# TODO

This file separates the implementation roadmap from its supporting decisions and verification. Roadmap items produce working increments. The detailed backlog resolves only the choices needed by the active increment.

## Implementation roadmap

### 0. Deliver the walking skeleton

This deliberately thin slice proves both complete ingestion paths with one live post and one backfilled post before hardening any component.

- [x] Start `spex` with a minimal Textual main process and one status view.
- [ ] Remove the obsolete Typer runtime dependency from the package configuration.
- [ ] Launch skeletal ingestion, validation-and-transformation, and Streamlit child processes through the final process boundaries.
- [ ] Start live ingestion through the TUI and capture one `app.bsky.feed.post` event from Jetstream.
- [ ] Read the archive credential from the test environment and start a minimal post backfill through the TUI.
- [ ] Capture one backfilled `app.bsky.feed.post` event from the Jetstream archive.
- [ ] Pass both events through the same replaceable raw-store interface backed by a minimal JSON Lines implementation.
- [ ] Validate that both events decode and contain the fields required by the slice.
- [ ] Transform both post texts through the same analytical mapping.
- [ ] Insert both mutations into one minimal DuckLake table.
- [ ] Show service health in the Textual status view.
- [ ] Show a table of posts and post counts grouped by DID from DuckLake in Streamlit.
- [ ] Add end-to-end verification that traces one live record and one backfilled record through their ingestion paths, shared transformation, DuckLake, and Streamlit.
- [ ] Record every deferred production concern in the supporting backlog without expanding the slice.

The slice excludes persistent credential storage, complete collection coverage, raw-store selection, recovery hardening, retention cleanup, performance tuning, and cross-platform validation.

### 1. Harden the application foundation

- [ ] Stabilize the package entry point and replace slice-local paths with the cross-platform `platformdirs` layout.
- [ ] Add configuration loading, validation, and persistence.
- [ ] Add structured logging and the standard retry utility.
- [ ] Add the cross-platform process-lock interface and lock metadata.
- [ ] Verify paths, permissions, lock exclusivity, and process-exit release on every supported platform.

### 2. Harden the main process and worker contract

- [ ] Expand the walking-skeleton Textual control plane to own child-process orchestration.
- [ ] Generalize skeletal child launch into reusable worker supervision.
- [ ] Harden control connections with authentication and platform-specific AF_UNIX or AF_PIPE transport.
- [ ] Complete hello, readiness, heartbeat, shutdown, restart, and orphan-cleanup flows.
- [ ] Persist command state in the session request ledger.
- [ ] Verify the complete worker lifecycle before adding pipeline behavior.

### 3. Establish reproducible pipeline input

- [ ] Capture and profile representative Jetstream events for the five selected collections.
- [ ] Add the development-only replay source with original and accelerated timing.
- [ ] Record provenance and reproducibility metadata with each captured dataset.

### 4. Select and establish raw retention

- [ ] Build equivalent JSON Lines and SQLite WAL benchmark prototypes.
- [ ] Run the agreed write, read, recovery, cleanup, and concurrency workload while measuring settled and peak disk use, including SQLite WAL and retained free pages.
- [ ] Benchmark sealed `.jsonl.zst` ingestion through in-memory DuckDB JSON flattening into DuckLake.
- [ ] Select the raw-retention format from recorded evidence.
- [ ] Build the selected raw-store boundary with capacity control, checkpoints, replay, and confirmed-consumption deletion.

### 5. Deliver the live vertical slice

- [ ] Connect live ingestion to Jetstream with the fixed collection filter.
- [ ] Persist live events through the raw-store boundary.
- [ ] Validate and transform one profiled collection.
- [ ] Insert mutation history and rejected records into DuckLake.
- [ ] Query the retained mutation and current-state views.
- [ ] Verify reconnection, replay, deduplication, and restart recovery end to end.

### 6. Complete pipeline coverage and retention

- [ ] Add validation and transformation for the remaining selected collections.
- [ ] Add scheduled and startup retention cleanup.
- [ ] Add graceful processing drain and in-flight batch commit.
- [ ] Verify out-of-order batches, rejection handling, capacity pauses, and cleanup failure recovery.

### 7. Deliver historical backfill

- [ ] Establish archive-bound probing and timeframe-to-sequence mapping.
- [ ] Add master-password-protected credential storage and session unlock.
- [ ] Connect authenticated backfill to the shared raw-store boundary.
- [ ] Verify concurrent live and backfill ingestion with overlap and out-of-order delivery.

### 8. Deliver operational control

- [ ] Connect the Textual interface to service lifecycle controls and aggregate health.
- [ ] Add retention, cleanup-interval, raw-capacity, and credential configuration workflows.
- [ ] Add persistent warnings, degraded states, manual retries, and rejection counts.
- [ ] Verify shutdown, replacement startup, worker recovery, and configuration persistence.

### 9. Deliver analytical views

- [ ] Implement the selected Streamlit questions as read-only DuckLake views.
- [ ] Add empty, loading, unavailable, and query-failure states.
- [ ] Verify dashboard behavior throughout ingestion, cleanup, and service outages.

### 10. Validate and present the system

- [ ] Run the functional, failure, cross-platform, and stored-data scale suites.
- [ ] Record throughput, processing capacity, end-to-end lag, storage behavior, and query responsiveness.
- [ ] Publish selected Markdown benchmark summaries.
- [ ] Complete the portfolio demonstrations and supporting documentation.

## Supporting decisions and verification

Resolve these items when their roadmap increment becomes active.

## 0. Release intent and constraints

- [x] Use a direct entry point into the Textual control plane with no structured headless command interface.
- [x] Supervise each named service through a direct `multiprocessing.Process` handle.
- [x] Run blocking process and connection supervision through Textual `@work(thread=True)` functions.
- [x] Return control-thread state through `post_message()` or `call_from_thread()`.
- [x] Define walking-skeleton completion as a runnable application that starts the TUI and orchestrator, activates live ingestion, backfill, and processing, and displays transformed data in Streamlit.
- [x] Prove live and backfill ingestion through the same downstream storage and processing path.
- [x] Read the archive credential from an environment variable while testing the slice and defer persistent encrypted credential storage.
- [x] Limit the first analytical record to post text.
- [x] Limit the first TUI status view to service health.
- [x] Select a table of posts as the first Streamlit view.
- [x] Include post counts grouped by DID in the first Streamlit view.
- [x] Retain public Jetstream data without anonymization in local Spex storage.
- [x] Define the initial demonstration as an extremely basic working data pipeline.
- [x] Verify that one live post and one backfilled post decode, ingest, transform, persist, and appear in Streamlit.

## 1. Shared platform foundation

### Paths, configuration, and logging

- [ ] Define the application-data, configuration, runtime, raw-data, dataset, benchmark, and log paths resolved through `platformdirs`.
- [ ] Define configuration persistence and validation boundaries.
- [ ] Define service health, metrics, logging, and tracing conventions.
- [ ] Define structured command-failure details for logs and TUI health.

### Process identity and locking

- [ ] Preserve layer dependency rules while decomposing implementation modules.
- [ ] Test advisory-lock exclusivity and process-exit release on Linux, macOS, Windows, and WSL.
- [ ] Test stable in-place JSON lock-metadata writes and concurrent reads.
- [ ] Test session-ID stability across worker restarts and renewal across orchestrator replacement.
- [ ] Test service-instance ID renewal and main-process session-ID reuse.
- [ ] Define and test cross-platform process-identity validation for forced orchestrator termination.
- [ ] Test current-session process-handle restart and old-session manual-intervention fallback.
- [ ] Test all-service orphan discovery, heartbeat-window shutdown, and platform-specific forced termination.
- [ ] Test degraded health when an orphan cannot be terminated.
- [ ] Test the replacement-startup race between final lock retry and old-worker heartbeat-loss shutdown.

## 2. Orchestrator and control plane

### Process lifecycle

- [ ] Define process readiness and shutdown behavior.
- [ ] Define TUI controls for starting and stopping live ingestion and backfill.
- [ ] Test automatic validation-and-transformation startup with either ingestion service.
- [ ] Test graceful child shutdown after main-process loss.
- [ ] Test worker restart exhaustion, degraded health, and manual restart.

### IPC transport and protocol

- [ ] Define AF_UNIX and AF_PIPE addresses and same-user endpoint permissions.
- [ ] Validate memory-only IPC authentication-key transfer under each supported multiprocessing start method.
- [ ] Define the IPC protocol-version representation and negotiation error schema.
- [ ] Define strict UTF-8 JSON message schemas and error responses.
- [ ] Define and test `hello` and `hello_ack`, lock-backed validation, five-second timeouts, and readiness transition.
- [ ] Test session and service identity tagging, connection association, mismatch rejection, health display, and log correlation.
- [ ] Test duplicate connection rejection and same-instance reconnection.
- [ ] Define and test heartbeat acknowledgments and three-miss connection failure.
- [ ] Test exhausted IPC reconnection, degraded status, and manual service restart.
- [ ] Review the absence of an IPC message-size limit if the trust boundary changes.

### Command lifecycle and request ledger

- [ ] Define command response schemas and allowed request states.
- [ ] Finalize manual retry identity behavior during IPC implementation.
- [ ] Define SQLite constraints for message ID, status, creation time, and last-update time.
- [ ] Define partial-success and crash handling for concurrent command dispatch and ledger insertion.
- [ ] Test same-ID dispatch retries and replacement ledger writes with current status.
- [ ] Test idempotent duplicate-request handling.
- [ ] Test late acceptance, completion, and failure reconciliation for unknown requests.
- [ ] Test direct manual retry after ledger expiration.
- [ ] Test degraded ledger health while commands continue and automatic recovery after a successful write.
- [ ] Test WAL mode under SQLite lock and busy conditions.
- [ ] Test schema-version mismatch recreation.
- [ ] Test runtime corruption disposal, automatic ledger recreation, and health recovery.
- [ ] Test request-ledger cleanup target validation and symbolic-link refusal.
- [ ] Test exhausted prior-session deletion while a fresh session ledger operates.
- [ ] Test disk-full and I/O retry exhaustion while commands continue.
- [ ] Validate inherited Windows permissions for the per-user ledger directory.
- [ ] Profile command completion durations and select command-specific timeouts.

## 3. Test-data and profiling foundation

- [ ] Define the captured Jetstream corpus used for data profiling and scale tests.
- [ ] Define capture retention, sanitization, and access rules.
- [ ] Define the dataset subdirectory within the per-user application-data directory.
- [ ] Define reproducibility metadata and record the source Jetstream instance.
- [ ] Validate sequence uniqueness across captured live and archive events from `jetstream.us-east.bsky.network`.
- [ ] Define development-only original-timing and accelerated replay controls and target event rates.
- [ ] Define performance measurements and acceptance criteria for each pipeline stage.
- [ ] Separate network-bound integration results from stored-data scale-test results.
- [ ] Define the Markdown benchmark-result schema and publication workflow for selected runs.

## 4. Ephemeral raw-retention boundary

This phase is a research gate for ingestion and downstream batch processing.

- [ ] Define the raw-retention workload and acceptance criteria.
- [ ] Benchmark JSON Lines against SQLite in WAL mode for sustained writes, replay reads, crash recovery, cleanup, settled and peak storage overhead, out-of-order arrivals, and concurrent access.
- [ ] Select the ephemeral raw-retention format from benchmark evidence.
- [ ] Define persistence and replay behavior between ingestion and processing.
- [ ] Define raw-capacity enforcement, pause, and resume behavior.
- [ ] Define how the pipeline confirms data-mart or rejected-record consumption before deleting raw events.
- [ ] Define durable state-artifact names for live ingestion and backfill if JSON Lines is selected.
- [ ] Define deterministic state reconstruction if JSON Lines is selected.
- [ ] Benchmark per-line and grouped durable sync while preserving record-before-checkpoint ordering if JSON Lines is selected.
- [ ] Profile validation and transformation batch sizes against the 100 MiB rotation boundary if JSON Lines is selected.

## 5. Live ingestion

- [ ] Define the live-ingestion component contract.
- [ ] Define live connection, reconnection, and checkpoint behavior.
- [ ] Define how first-run ingestion discovers the oldest unsealed sequence within retention.
- [ ] Design durable sequence checkpoints and idempotent replay.
- [ ] Define collection filtering for posts, reposts, likes, blocks, and follows.
- [ ] Test raw-capacity pause and resume without intentional event loss.
- [ ] Test checkpoint recovery, inclusive replay, and downstream deduplication.

## 6. Validation and transformation

- [ ] Define the combined processing-service contract.
- [ ] Profile posts, reposts, likes, blocks, and follows.
- [ ] Define validation rules and the first-error behavior.
- [ ] Define transformation outputs and normalization rules.
- [ ] Define explicit DuckDB JSON schemas and flattening queries for each selected collection.
- [ ] Define the rejected-record schema for validation and transformation failures.
- [ ] Define failure handling and standard-retry boundaries.
- [ ] Profile representative graceful-drain workloads and select a timeout.
- [ ] Test in-flight batch commit during shutdown and revisit the absence of a hard timeout if stalls occur.

## 7. DuckLake data mart

- [ ] Define the DuckLake table layout and ownership boundaries.
- [ ] Define the mutation-history schema and natural-key constraints.
- [ ] Define data-mart deduplication identity and conflict behavior.
- [ ] Define within-batch ordering and out-of-order cross-batch behavior.
- [ ] Define the rejected-record table and retention integration.
- [ ] Define dataset retention, deletion, and storage limits.
- [ ] Define startup and scheduled cleanup behavior.
- [ ] Define query-time current-state projection semantics.
- [ ] Define query-performance criteria that justify materializing current state.
- [ ] Define how Streamlit receives read-only DuckLake access.

## 8. Historical backfill and credential security

- [ ] Define the backfill component contract.
- [ ] Probe available archive bounds and record observed behavior.
- [ ] Select default `afterSeq` and `beforeSeq` bounds.
- [ ] Determine how user-selected timeframes map to Jetstream sequence bounds.
- [ ] Define how the TUI reports variable archive availability against configured retention.
- [ ] Select the authenticated-encryption format and library for the master-password-protected credential file.
- [ ] Select the password-based key-derivation algorithm and parameters.
- [ ] Define credential-file location, permissions, corruption handling, and migration.
- [ ] Define secure credential transfer from the main process to backfill.
- [ ] Validate encrypted credential storage on Linux, Windows, macOS, and Arch Linux under WSL.
- [ ] Test concurrent live and backfill ingestion with overlapping and out-of-order events.

## 9. Textual operational interface

- [ ] Define the TUI information architecture and control workflow.
- [ ] Define how the TUI obtains service state and metrics.
- [ ] Define retained rejection counts and cleanup-failure details.
- [ ] Define the retention-setting workflow and validation.
- [ ] Define retention-increase backfill offers and retention-decrease data-loss confirmation.
- [ ] Define raw-capacity configuration and available-disk display.
- [ ] Define credential setup and backfill unlock workflows.
- [ ] Define persistent and acknowledgment-cleared warnings.

## 10. Streamlit analytical interface

- [ ] Convert the initial analytical questions into dashboard views.
- [ ] Define dashboard query contracts against DuckLake.
- [ ] Define empty, loading, unavailable, and query-failure states.
- [ ] Validate that Streamlit remains analytical and read-only.

## 11. Integrated verification and portfolio evidence

- [ ] Run functional tests for component contracts and end-to-end data flow.
- [ ] Run failure tests for service isolation, restart exhaustion, storage exhaustion, and recovery.
- [ ] Run cross-platform tests for installation, paths, locks, IPC, credentials, and shutdown.
- [ ] Run stored-data scale tests with captured Jetstream events.
- [ ] Measure sustained ingestion throughput, processing capacity, end-to-end lag, and query responsiveness.
- [ ] Publish selected benchmark summaries under `docs/benchmarks/`.
- [ ] Validate the portfolio demonstrations and evaluation criteria.
- [ ] Refine structural dependencies when implemented component contracts introduce new cross-component requirements.
