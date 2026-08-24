# TODO

This file separates the implementation roadmap from its supporting decisions and verification. Roadmap items produce working increments. The detailed backlog resolves only the choices needed by the active increment.

## Implementation roadmap

The active control-plane rewrite follows the file-by-file checklist in [Control-plane refactor TODO](REFACTOR_TODO.md).

### 0. Deliver the walking skeleton

This deliberately thin slice proves both ingestion phases with one replayed post and one live post before hardening any component.

#### 0.1 Complete the executable foundation

- [x] Create a minimal Textual interface with one status view.
- [x] Remove the obsolete Typer runtime dependency from the package configuration.
- [x] Select Streamlit and `platformdirs` as additional dependencies required by the slice.
- [ ] Replace direct `websockets` and HTTPX ingestion use with a pinned `atproto` release containing `atproto_jetstream` and refresh `uv.lock`.
- [x] Use the `spawn` multiprocessing context on every supported platform.
- [x] Create importable service scaffolds for live ingestion, backfill, validation and transformation, and Streamlit; the separate ingestion scaffolds are now transitional.
- [x] Replace the live and backfill scaffolds with one ingestion service under the `ingest` role.
- [x] Resolve M0 raw files and DuckLake data under the Spex application-data directory provided by `platformdirs`.
- [x] Define the exact M0 data, configuration, and runtime paths beneath the resolved `platformdirs` roots.
- [x] Bootstrap the accepted directory tree before starting application processes.
- [ ] Validate M0 path creation and isolation on Linux and WSL.

#### 0.2 Establish the minimal control plane

- [x] Define the walking-skeleton service state as running or stopped, with ingestion additionally reporting `replay` or `live`.
- [ ] Create the dedicated main-process orchestrator and explicit `spawn` context.
- [ ] Create a dedicated duplex control pipe before spawning each child.
- [x] Remove the obsolete runtime IPC, ports, and child-lock directories from application bootstrap.
- [ ] Spawn Textual as a non-daemonic IPC spoke with inherited terminal streams.
  Blocked: a real `spex` PTY run confirms that Python's spawned multiprocessing child closes standard input, and Textual fails when its Linux driver calls `sys.__stdin__.fileno()`.
- [ ] Complete the TUI initial-state, shutdown-request, pipe-loss, and exit lifecycle.
- [ ] Handle `SIGTERM` in the TUI process with a handler that exits the Textual app so an abnormal Hub shutdown restores the terminal.
- [ ] Define the walking-skeleton service transitions.
- [ ] Add a Textual control for starting and stopping ingestion.
- [ ] Show ingestion's `replay` or `live` phase.
- [ ] Start validation and transformation automatically with ingestion.
- [ ] Launch every child with `multiprocessing.Process` and retain its process handle.
- [ ] Monitor orchestrator-owned child pipe endpoints independently of Textual.
- [ ] Retain each parent pipe endpoint under the role and process instance launched by the Hub.
- [x] Define the minimal control and health messages needed by the slice.
- [ ] Return IPC state changes through Textual's `post_message()` or `call_from_thread()` boundary.
- [ ] Show actual child-process and connection state in the Textual status view.
- [ ] Treat Textual closure as an application-shutdown request and stop all children through the orchestrator.

#### 0.3 Establish the shared storage path

- [ ] Define the minimal JSON Lines event envelope and completed-file handoff used by ingestion and processing.
- [ ] Implement a replaceable raw-store interface backed by the minimal JSON Lines path.
- [ ] Keep one raw writer and one durable ingestion cursor across replay and live.
- [ ] Define the minimal DuckLake catalog, database, schema, and posts table required by the slice.
- [ ] Define how processing confirms a raw event is represented in DuckLake for the slice.

#### 0.4 Complete ingestion

- [ ] Add and pin an `atproto` release containing `atproto_jetstream`.
- [ ] Connect to the fixed Jetstream v2 endpoint with one ingestion service.
- [ ] Subscribe only to `app.bsky.feed.post` without a DID filter.
- [ ] Read the test archive credential from an environment variable without persisting it.
- [ ] Use `atproto_jetstream.replay()` to receive and persist one replayed post mutation.
- [ ] Confirm the SDK transitions to the live tail and receive one live post mutation.
- [ ] Persist one cursor across both phases.
- [ ] Report ingestion state, `replay` or `live` phase, and failure to Textual.

#### 0.5 Confirm replay and live behavior

- [ ] Confirm replay's exclusive lower cursor bound and the SDK-managed inclusive live cutover.
- [ ] Confirm seam and reconnect redelivery are suppressed by the SDK cursor.
- [ ] Confirm crash recovery can replay durable raw records and remains idempotent downstream.
- [ ] Confirm live-only operation starts in `live` when archive access is unavailable.

#### 0.6 Complete processing and persistence

- [ ] Read completed raw input from ingestion.
- [ ] Decode the Jetstream commit envelope and `app.bsky.feed.post` record.
- [ ] Validate only the envelope, DID, record identity, text, and timestamps required by the slice.
- [ ] Transform replayed and live posts through one mapping.
- [ ] Preserve enough source identity to trace each output row to its Jetstream mutation.
- [ ] Insert both phase examples into the minimal DuckLake posts table.
- [ ] Report processing and persistence state or failure to Textual.

#### 0.7 Complete the analytical view

- [ ] Launch Streamlit as a supervised child process.
- [ ] Detect Hub loss in the dashboard through pipe EOF, replacing the placeholder loop that never reads its pipe.
- [ ] Open DuckLake through a read-only dashboard boundary.
- [ ] Display the posts table.
- [ ] Display post counts grouped by DID.
- [ ] Represent empty and unavailable data without crashing the dashboard.

#### 0.8 Verify and close the slice

- [ ] Trace one live record from Jetstream through raw storage, processing, DuckLake, and Streamlit.
- [ ] Trace one replayed record through the same downstream path.
- [ ] Confirm the displayed rows retain the identity of the ingested mutations.
- [ ] Confirm Textual remains responsive while its IPC reader and service work run.
- [ ] Confirm closing Textual causes the orchestrator to stop and join every child process.
- [ ] Record every deferred production concern in the supporting backlog without expanding the slice.

The slice excludes persistent credential storage, complete collection coverage, raw-store selection, recovery hardening, retention cleanup, performance tuning, and supported-environment validation.

### 1. Harden the application foundation

- [ ] Stabilize the package entry point and expand the initial `platformdirs` layout for every application path.
- [ ] Add configuration loading, validation, and persistence.
- [ ] Add structured logging and the standard retry utility.
- [ ] Add the `fcntl.flock` process-lock interface and lock metadata.
- [ ] Verify paths, permissions, lock exclusivity, and process-exit release on Linux and WSL.

### 2. Harden the main process and worker contract

- [ ] Expand the walking-skeleton orchestrator to own child-process supervision and authoritative control state.
- [ ] Generalize skeletal child launch into reusable worker supervision.
- [ ] Harden duplex-pipe ownership, closure, and concurrent-send behavior.
- [ ] Complete readiness, shutdown, restart, and pipe-loss flows.
- [ ] Track command state in the ephemeral session request ledger.
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

### 5. Deliver the ingestion vertical slice

- [ ] Connect ingestion to Jetstream with the fixed collection filter.
- [ ] Persist replayed and live events through one raw-store boundary.
- [ ] Validate and transform one profiled collection.
- [ ] Insert mutation history and rejected records into DuckLake.
- [ ] Query the retained mutation and current-state views.
- [ ] Verify replay-to-live transition, reconnection, deduplication, and restart recovery end to end.

### 6. Complete pipeline coverage and retention

- [ ] Add validation and transformation for the remaining selected collections.
- [ ] Add scheduled and startup retention cleanup.
- [ ] Add graceful processing drain and in-flight batch commit.
- [ ] Verify out-of-order batches, rejection handling, capacity pauses, and cleanup failure recovery.

### 7. Complete replay and credentials

- [ ] Establish archive-bound probing and timeframe-to-sequence mapping.
- [ ] Add master-password-protected credential storage and session unlock.
- [ ] Connect authenticated replay to the ingestion service.
- [ ] Verify archive replay and the transition to live through one cursor and raw writer.

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

- [ ] Run the functional, failure, Linux, WSL, and stored-data scale suites.
- [ ] Record throughput, processing capacity, end-to-end lag, storage behavior, and query responsiveness.
- [ ] Publish selected Markdown benchmark summaries.
- [ ] Complete the portfolio demonstrations and supporting documentation.

## Supporting decisions and verification

Resolve these items when their roadmap increment becomes active.

## 0. Release intent and constraints

- [x] Use a direct entry point into the main-process orchestrator with no structured headless command interface.
- [x] Supervise each named service through a direct `multiprocessing.Process` handle.
- [x] Assign listener ownership and connection monitoring to the dedicated main-process orchestrator.
- [x] Return TUI connection-reader state through `post_message()` or `call_from_thread()`.
- [x] Define walking-skeleton completion as a runnable application that starts the TUI and orchestrator, activates ingestion and processing, and displays replayed and live data in Streamlit.
- [x] Prove replay and live ingestion through the same downstream storage and processing path.
- [x] Read the archive credential from an environment variable while testing the slice and defer persistent encrypted credential storage.
- [x] Limit the first analytical record to post text.
- [x] Limit the first TUI status view to service health.
- [x] Select a table of posts as the first Streamlit view.
- [x] Include post counts grouped by DID in the first Streamlit view.
- [x] Retain public Jetstream data without anonymization in local Spex storage.
- [x] Define the initial demonstration as an extremely basic working data pipeline.
- [x] Verify that one replayed post and one live post decode, ingest, transform, persist, and appear in Streamlit.

## 1. Shared platform foundation

### Paths, configuration, and logging

- [ ] Define the application-data, configuration, runtime, raw-data, dataset, benchmark, and log paths resolved through `platformdirs`.
- [ ] Define configuration persistence and validation boundaries.
- [ ] Define service health, metrics, logging, and tracing conventions.
- [x] Select centralized orchestrator logging through an unbounded multiprocessing queue and one listener thread.
- [x] Select one combined JSON Lines application log with hourly rotation.
- [x] Limit initial dashboard logging to Spex service records and exclude Streamlit framework output.
- [x] Control the log level and expose a log readout through the TUI.
- [x] Rotate logs hourly, retain ten rotated files, and compress rotated files with Zstandard.
- [x] Use one global TUI log level and drain queued logs after every child exits during shutdown.
- [x] Include a stable machine-readable event name and a human-readable message in every log record.
- [x] Feed the TUI log readout from the persisted combined JSON Lines log.
- [ ] Define active-log following, the TUI reader transition after orchestrator-owned rotation, refresh cadence, remaining structured fields, Zstandard implementation, filenames, and TUI readout behavior.
- [ ] Define structured command-failure details for logs and TUI health.

### Process identity and locking

- [ ] Preserve layer dependency rules while decomposing implementation modules.
- [x] Avoid Textual stream-capture interference by creating multiprocessing resources and children from a dedicated main-process orchestrator.
- [x] Assign the spawned Textual spoke to the main-process orchestrator.
- [ ] Verify spawned Textual terminal input, rendering, resize handling, graceful exit, hub-loss exit, terminal restoration, and return-code propagation on Linux and WSL.
- [ ] Test advisory-lock exclusivity and process-exit release on Linux and WSL.
- [ ] Test stable in-place Hub-lock metadata writes and concurrent reads.
- [ ] Test session-ID stability across worker restarts and renewal across orchestrator replacement.
- [ ] Test service-instance ID renewal, main-process session-ID reuse, and per-process logging context.
- [ ] Define and test Linux and WSL process-identity validation for forced Hub termination.
- [ ] Test current-session process-handle restart and old-session manual-intervention fallback.
- [ ] Test child shutdown after Hub pipe loss and forced termination through retained process handles.

## 2. Orchestrator and control plane

### Process lifecycle

- [ ] Define process readiness and shutdown behavior.
- [ ] Define the TUI control for starting and stopping ingestion.
- [ ] Test automatic validation-and-transformation startup with ingestion.
- [ ] Test graceful child shutdown after main-process loss.
- [ ] Test worker restart exhaustion, degraded health, and manual restart.

### IPC transport and protocol

- [ ] Verify duplex `Connection` transfer under the explicit `spawn` context.
- [ ] Verify that both processes close unused pipe endpoints and detect peer loss through EOF.
- [ ] Define the readiness protocol-version representation and mismatch response.
- [ ] Define the native dictionary payloads and error responses required by the walking skeleton.
- [ ] Define and test initial-state validation and readiness transition.
- [ ] Test connection-bound service identity, health display, and log correlation.
- [ ] Test one pipe per process instance and fresh-pipe creation on restart.
- [ ] Test pipe loss, degraded status, and manual service restart.
- [ ] Review pickle trust and the absence of an IPC message-size limit if the inherited-pipe boundary changes.

### Command lifecycle and ephemeral request ledger

- [ ] Define command response schemas and allowed request states.
- [ ] Finalize manual retry identity behavior during IPC implementation.
- [ ] Define the in-memory entry structure for message ID, status, creation time, and last-update time.
- [ ] Test recording a request before dispatch and updating its current status.
- [ ] Test idempotent duplicate-request handling.
- [ ] Test late acceptance, completion, and failure reconciliation for unknown requests.
- [ ] Test direct manual retry after ledger expiration.
- [ ] Test one-hour entry expiration and complete disposal on Hub exit.
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
- [ ] Define the ingestion state-artifact name if JSON Lines is selected.
- [ ] Define deterministic state reconstruction if JSON Lines is selected.
- [ ] Benchmark per-line and grouped durable sync while preserving record-before-checkpoint ordering if JSON Lines is selected.
- [ ] Profile validation and transformation batch sizes against the 100 MiB rotation boundary if JSON Lines is selected.

## 5. Ingestion

- [ ] Define the ingestion component contract and its `replay` and `live` phases.
- [ ] Pin the minimum `atproto` version that supplies the required `atproto_jetstream` API.
- [ ] Define replay, live connection, reconnection, and durable-cursor behavior.
- [ ] Define how first-run ingestion maps retention to its replay cursor.
- [ ] Design durable cursor persistence and idempotent crash recovery.
- [ ] Define collection filtering for posts, reposts, likes, blocks, and follows.
- [ ] Test raw-capacity pause and resume without intentional event loss.
- [ ] Test SDK seam deduplication, cursor recovery, inclusive replay after crashes, and downstream deduplication.

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

## 8. Replay and credential security

- [ ] Define replay configuration within the ingestion contract.
- [ ] Probe available archive bounds and record observed behavior.
- [ ] Select the default replay `after_seq` cursor.
- [ ] Determine how user-selected timeframes map to Jetstream sequences.
- [ ] Define how the TUI reports variable archive availability against configured retention.
- [ ] Select the authenticated-encryption format and library for the master-password-protected credential file.
- [ ] Select the password-based key-derivation algorithm and parameters.
- [ ] Define credential-file location, permissions, corruption handling, and migration.
- [ ] Define secure credential transfer from the main process to ingestion.
- [ ] Validate encrypted credential storage on Linux and Arch Linux under WSL.
- [ ] Test replay-to-live cutover, reconnect deduplication, and live-only operation.

## 9. Textual operational interface

- [ ] Define the TUI information architecture and control workflow.
- [ ] Define how the TUI obtains service state and metrics.
- [ ] Define retained rejection counts and cleanup-failure details.
- [ ] Define the retention-setting workflow and validation.
- [ ] Define retention-increase replay offers and retention-decrease data-loss confirmation.
- [ ] Define raw-capacity configuration and available-disk display.
- [ ] Define credential setup and replay unlock workflows.
- [ ] Define persistent and acknowledgment-cleared warnings.

## 10. Streamlit analytical interface

- [ ] Convert the initial analytical questions into dashboard views.
- [ ] Define dashboard query contracts against DuckLake.
- [ ] Define empty, loading, unavailable, and query-failure states.
- [ ] Validate that Streamlit remains analytical and read-only.

## 11. Integrated verification and portfolio evidence

- [ ] Run functional tests for component contracts and end-to-end data flow.
- [ ] Run failure tests for service isolation, restart exhaustion, storage exhaustion, and recovery.
- [ ] Run Linux and WSL tests for installation, paths, locks, IPC, credentials, and shutdown.
- [ ] Run stored-data scale tests with captured Jetstream events.
- [ ] Measure sustained ingestion throughput, processing capacity, end-to-end lag, and query responsiveness.
- [ ] Publish selected benchmark summaries under `docs/benchmarks/`.
- [ ] Validate the portfolio demonstrations and evaluation criteria.
- [ ] Refine structural dependencies when implemented component contracts introduce new cross-component requirements.
