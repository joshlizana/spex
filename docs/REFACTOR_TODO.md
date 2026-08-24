# Control-plane refactor TODO

Status: complete

This checklist replaces listener-based IPC with Hub-created duplex pipes while preserving a reviewable, file-at-a-time workflow. Joshua implements application behavior. Agents review each completed file and maintain its documentation, comments, and docstrings.

## Resume here

Steps 1 through 12 contain the completed direct-pipe work. Textual runs in the main process, owns the Hub process handle, and communicates with it through one direct pipe. The Hub owns ingestion, pipeline, and dashboard.

The target topology has one `ingest` service with exactly two phases: `replay` and `live`. `atproto_jetstream.replay()` owns archive planning, decoding, seam deduplication, and the transition to the WebSocket tail. Backfill is no longer a service identity.

The consolidated ingestion and processing workers implement the reviewed worker lifecycle: no `pause`/`resume`, spawn-only `start`, signal-based `stop`, and pipe-EOF Hub-loss detection from a daemon monitor thread.

TUI and dashboard don't fit that pattern — both are long-lived and non-cyclic, so each monitors its pipe from a daemon thread. Textual exits through its own interface, closes the Hub pipe, and joins the Hub. Hub EOF crosses Textual's thread-safe boundary and exits the TUI. The TUI remains the one genuine two-way exception for messaging.

Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so while the TUI runs, Ctrl-C delivers a literal `\x03` byte to the TUI and no `SIGINT` to any process in the foreground group, including the Hub. Spex currently has no binding for that byte, so it is ignored. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`. Exit through the TUI interface is therefore the only normal shutdown path.

The TUI monitors its child endpoint from a daemon thread. Pipe EOF crosses Textual's thread boundary with `call_from_thread()` and exits the application. No request ledger is needed because the TUI exposes no service-lifecycle commands.

## Confirmed target

- Textual creates and retains the Hub process handle. The Hub creates and retains every operational-service process handle.
- Textual creates its Hub pipe; the Hub creates a duplex `multiprocessing.Pipe` for every operational child and passes one endpoint during spawn.
- The Hub and the TUI exchange native Python dictionaries with `Connection.send()` and `Connection.recv()`. Ingestion and processing send advisory telemetry, including ingestion's phase, but receive no commands. Dashboard sends no messages.
- Pipe ownership supplies service identity for every child. Messages contain `type`, `payload`, and a `message_id` only for correlated exchanges — only the TUI ever sends one.
- Pipe EOF is the only signal of Hub loss for ingestion and processing, checked from a daemon monitor thread. It also serves the dashboard. The TUI's monitor thread exits Textual on EOF. Process sentinels report every child's exit regardless.
- A worker's monitor observes only Hub-to-worker traffic, so receiving after `poll()` remains sound while the Hub sends no commands. The Hub must `recv()` worker telemetry and treat `EOFError` as child loss once telemetry exists.
- Ingestion and processing stop, when the Hub is alive and initiates it, through a shared `ServiceProcess` `SIGTERM` handler that ends the current work cycle gracefully; the Hub triggers it with `process.terminate()`, not a pipe message.
- The TUI stops by exiting through its own interface; the Hub detects that child loss and shuts down. The dashboard stops through `SIGTERM`/`SIGINT` without a handler, since it holds no in-flight state.
- No request state is kept — commands are one-off and fire-and-forget, nothing to track or discard.
- Only the Hub acquires `hub.lock` directly beneath the `platformdirs` runtime directory.
- Process identity remains implicit in Hub-owned process handles and pipe endpoints.

Reference an item by its step number and letter, such as 8e for the Hub's supervision loop.

## Working rule

Complete and review one numbered file step before beginning the next. Keep each intermediate step importable. Record an intentional temporary integration gap in this checklist when a later step must close it.

Guard expected architectural boundaries: pipe closure, child-process exit, partial resource acquisition, and failures crossing a thread boundary. Let ordinary programming errors surface naturally. Add narrower defensive handling when testing or observed failures establish a need. This includes timeout and retry criteria: defer them until an observed failure demonstrates the need, and let an unmatched or malformed internal message crash the Hub during this stage rather than degrade gracefully.

The TUI monitors its pipe for Hub loss but sends no operator traffic yet. What the TUI sends is implementation, tracked in `docs/TODO.md` 0.2. The `spex` entry point bootstraps the filesystem, runs Textual in the main process, and spawns the Hub under its async context. No ledger gap exists — none is needed.

## File sequence

### 1. `src/spex/bootstrap.py`

- [x] a. Remove creation of the obsolete `locks` and `ipc` runtime subdirectories.
- [x] b. Keep creation of accepted data, configuration, state, log, cache, and runtime roots.
- [x] c. Align comments and formatting with the resulting directory layout.
- [x] d. Review the file before continuing.

### 2. `src/spex/services/lock.py`

- [x] a. Restrict the lock to Hub application ownership.
- [x] b. Resolve `hub.lock` directly beneath the runtime directory.
- [x] c. Retain PID and process start time as lock metadata.
- [x] d. Remove session, child-role, and instance metadata.
- [x] e. Preserve advisory acquisition, complete writes, synchronization, and descriptor cleanup.
- [x] f. Align the class name, API, comments, and docstrings with its single purpose.
- [x] g. Review the file before continuing.

### 3. `src/spex/services/ipc_client.py`

- [x] a. Delete the generic IPC client rather than preserving an abstraction without demonstrated reuse.
- [x] b. Keep service-specific pipe handling with each spoke until stable duplication supports extraction.
- [x] c. Confirm no source file imports `ipc_client` or `ServiceClient`.
- [x] d. Review the removal before continuing.

### 4. `src/spex/services/live.py`

Historical step, complete. The reviewed `LiveService` worker lifecycle now belongs to `IngestionService`; `live.py` is removed.

- [x] a. Accept the child pipe endpoint through process construction.
- [x] b. Never send or receive an application command on it; the base class monitors the pipe from a daemon thread and treats EOF as a stop signal.
- [x] c. Rely on the shared `ServiceProcess` signal handler for application shutdown; no worker control-message handling.
- [x] d. Drop the `paused` half of the state contract; the service is only running or stopped.
- [x] e. Close the pipe during every exit path.
- [x] f. Align comments and docstrings with scaffold behavior.
- [x] g. Review the file before continuing.

### 5. `src/spex/services/backfill.py`

Historical step, complete. `BackfillService` and `backfill.py` are removed; archive replay is the ingestion service's `replay` phase.

- [x] a. Apply the reviewed live-service control structure to backfill.
- [x] b. Drop the `paused` half of the state contract; the service is only running or stopped.
- [x] c. Close the pipe during every exit path.
- [x] d. Align comments and docstrings with scaffold behavior.
- [x] e. Review the file before continuing.

### 6. `src/spex/services/pipeline.py`

Complete, same basis as step 4.

- [x] a. Extract the shared worker process and pipe/signal stop lifecycle into `src/spex/services/service.py`, with the pipe used only for EOF-based Hub-loss detection.
- [x] b. Reduce the former live, backfill, and pipeline scaffolds to concrete `ServiceProcess` subclasses.
- [x] c. Make the pipeline scaffold compatible with Hub-owned process and pipe supervision.
- [x] d. Preserve its validation-and-transformation responsibility.
- [x] e. Add only the lifecycle behavior required by the walking skeleton.
- [x] f. Review the files before continuing.

### 7. `src/spex/services/dashboard.py`

Complete. `DashboardService` now subclasses `SpawnProcess` directly and accepts a pipe — a reversal of this step's original "no control-pipe behavior" target. No signal handling needed: dashboard is read-only display with no in-flight state, so an unhandled `SIGTERM`/`SIGINT`/immediate exit is acceptable, and its underlying framework may already handle signals on its own. Its actual scaffold behavior (`run()`'s real body) is `docs/TODO.md` 0.7 territory, not refactor scope — this checklist only covers whether it fits the Hub's process/pipe supervision model.

- [x] a. Subclass a spawnable `multiprocessing.Process` and accept the child pipe endpoint through construction.
- [x] b. The pipe carries loss detection in both directions: the dashboard learns of Hub loss through pipe EOF, and the Hub learns of dashboard exit through the same endpoint and the process sentinel. It carries no application messages.
- [x] c. Close the pipe during every exit path.
- [x] d. Align comments and docstrings with scaffold behavior.
- [x] e. Review the file before continuing.

`run()` monitors the pipe from a daemon thread while the placeholder dashboard body remains active. A spawned-process probe confirms that closing the Hub endpoint produces EOF and the dashboard exits cleanly with code zero.

### 8. `src/spex/services/hub.py`

- [x] a. Retain the explicit `spawn` context, Hub lock, process registry, and cleanup ownership.
- [x] b. Create one pipe pair before spawning each child.
- [x] c. Pass the child endpoint during spawn and close unused endpoint copies.
- [x] d. Store each parent endpoint with its role and process handle.
- [x] e. Monitor every pipe endpoint and process sentinel without listener or handler threads. `run()` is an `asyncio` supervision loop: `loop.add_signal_handler` records shutdown intent, TUI EOF ends supervision, and worker loss is joined without stopping the Hub. Blocking joins run through `asyncio.to_thread`, and `_join` escalates every child concurrently with `asyncio.gather`.
- [x] f. Require no request ledger because the TUI exposes no service-lifecycle commands.
- [x] g. Remove listener address, authentication key, listener lifecycle, and listener-shutdown messaging.
- [x] h. Preserve graceful join and forced-termination ownership.
- [x] i. Review the direct-pipe supervision mechanism. `_spawn_service` remains the uniform spawn path.
- [x] j. Replace the `live` and `backfill` registry roles with `ingest`; retain `pipeline`, `tui`, and `dashboard`.
- [x] k. Move ingestion and processing telemetry drainage to `docs/TODO.md` 0.2 with the telemetry producers. It is application behavior rather than transport-refactor mechanics; process sentinels remain authoritative for liveness.

### 9. `src/spex/services/tui.py`

- [x] a. Keep the Textual application in the service package and run it in the main process so it retains terminal input.
- [x] b. Create and retain the Hub process and TUI-Hub pipe. A daemon thread monitors Hub EOF and crosses Textual's thread-safe boundary with `call_from_thread()`.
- [x] c. Review the file before continuing. Normal and exceptional Textual exit stop and join the monitor, close the pipe, and join the Hub; partial process and thread startup clean up only acquired resources.

What the TUI does with that pipe is implementation, tracked in `docs/TODO.md` 0.2: receiving state across Textual's thread-safe boundary, showing real child and connection state in place of the placeholder health indicator, and reporting Hub startup failure. This step covers only the transport wiring.

### 10. `src/spex/__init__.py`

- [x] a. Bootstrap the filesystem and start Textual in the main process.
- [x] b. Let Textual create the Hub and let the Hub create the operational-service children.
- [x] c. Preserve the bare `spex` entry point.
- [x] d. Align the entry-point docstring with actual ownership.
- [x] e. Review the file before continuing. The entry point wraps Textual and its Hub child in one context-managed lifecycle.

### 11. Obsolete transport removal

- [x] a. Delete the obsolete `src/spex/services/hub/ipc_listener.py` module with the nested Hub package.
- [x] b. Delete the obsolete generic client artifact.
- [x] c. Confirm `orjson` is absent from control-plane transport. Its only use is `src/spex/services/lock.py`, writing lock metadata, which is not transport.
- [x] d. Confirm no code references listener addresses, authentication keys, hello messages, heartbeats, or runtime IPC paths.
- [x] e. Review the removal before continuing.

### 12. Integration checkpoint

These confirm the transport swap itself. Message traffic on the TUI's pipe is a feature, verified under `docs/TODO.md` 0.2.

- [x] a. Confirm every source module imports successfully. All ten source modules compile and import under the project environment.
- [x] b. Confirm the Hub acquires the single runtime lock. A temporary-path probe acquired the lock, rejected a second owner, and released it.
- [x] c. Confirm Textual spawns the Hub with a dedicated pipe and the Hub spawns ingestion, pipeline, and dashboard with distinct pipes.
- [x] d. Confirm process exit and Hub loss are observable. Spawned probes verify worker and dashboard EOF/sentinels; Textual observes Hub EOF through its monitor and retains the Hub process handle.
- [x] e. Confirm application shutdown closes endpoints and joins every child. A Hub probe starts all three services, stops and restarts pipeline, then closes the TUI endpoint; every process exits and the Hub returns code zero. A real PTY `spex` run exits through `q` with code zero.
- [x] f. Reconcile completed work with `docs/TODO.md`, design documents, decisions, `README.md`, and `CHANGELOG.md`.
