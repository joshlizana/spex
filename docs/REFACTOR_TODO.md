# Control-plane refactor TODO

Status: active

This checklist replaces listener-based IPC with Hub-created duplex pipes while preserving a reviewable, file-at-a-time workflow. Joshua implements application behavior. Agents review each completed file and maintain its documentation, comments, and docstrings.

## Resume here

Steps 1 through 6 are complete and stand. Step 7 is reopened; step 8 is partly done; step 9 is partly done — see each section below.

Target for live, backfill, and pipeline, now implemented: drop `pause`/`resume` entirely, a service is only running or stopped. `start` stays spawn-only. Operator-initiated `stop` moves to `process.terminate()` (`SIGTERM`) — `ServiceProcess` installs a shared handler so the current work cycle ends gracefully; each subclass still only differs in its unit of work per cycle. Each of the three still receives a Hub-owned pipe, but only to detect Hub loss: nothing is ever sent on it, and a non-blocking `poll()` once per work cycle (no background thread) is enough to notice EOF and stop the same way `SIGTERM` does.

TUI and dashboard don't fit that pattern — both are long-lived and non-cyclic (TUI blocks inside Textual's `app.run()`; dashboard has no bounded work cycle either), so neither can poll a pipe between cycles. Both are stopped by `SIGTERM`/`SIGINT` instead, with a handler that directly commands the app to exit rather than setting a flag. The TUI is still the one genuine two-way exception for messaging — it is the service started at launch rather than on operator command, and its pipe is meant to carry real operator-intent/state traffic once step 9 finishes — but its *shutdown* mechanism is signal-based like everything else now, not pipe-EOF-based.

Continue step 8 with Hub command dispatch and the in-memory request ledger. Keep the concrete request-ID representation unresolved until that implementation requires it. Complete the remaining Hub review before starting the TUI integration in step 9.

## Confirmed target

- The Hub creates every child process and retains its process handle.
- The Hub creates a duplex `multiprocessing.Pipe` for every child and passes one endpoint during spawn.
- The Hub and the TUI exchange native Python dictionaries with `Connection.send()` and `Connection.recv()`. Live, backfill, pipeline, and dashboard never send or receive a message on theirs.
- Pipe ownership supplies service identity for every child. Messages contain `type`, `payload`, and a `message_id` only for correlated exchanges — only the TUI ever sends one.
- Pipe EOF is the only signal of Hub loss for live, backfill, and pipeline, checked with a non-blocking `poll()` once per work cycle. It plays no role in stopping the TUI or dashboard — see below. Process sentinels report every child's exit regardless.
- Live, backfill, and pipeline stop, when the Hub is alive and initiates it, through a shared `ServiceProcess` `SIGTERM` handler that ends the current work cycle gracefully; the Hub triggers it with `process.terminate()`, not a pipe message.
- The TUI and dashboard stop through `SIGTERM`/`SIGINT`, since neither has a work cycle to poll a flag between — the handler commands the app to exit directly rather than setting a flag.
- The Hub keeps request state in memory and discards it when the application session ends.
- Only the Hub acquires `hub.lock` directly beneath the `platformdirs` runtime directory.
- Process identity remains implicit in Hub-owned process handles and pipe endpoints.

## Working rule

Complete and review one numbered file step before beginning the next. Keep each intermediate step importable. Record an intentional temporary integration gap in this checklist when a later step must close it.

Guard expected architectural boundaries: pipe closure, child-process exit, partial resource acquisition, and failures crossing a thread boundary. Let ordinary programming errors surface naturally. Add narrower defensive handling when testing or observed failures establish a need. This includes timeout and retry criteria: defer them until an observed failure demonstrates the need, and let an unmatched or malformed internal message crash the Hub during this stage rather than degrade gracefully.

Current integration gap: Hub's supervision loop and its in-memory request ledger remain unimplemented — `run()` is a stub pending the confirmed `asyncio` rewrite. `_handle_message` exists and dispatches `start`/`stop`, but nothing calls it yet.

## File sequence

### 1. `src/spex/bootstrap.py`

- [x] Remove creation of the obsolete `locks` and `ipc` runtime subdirectories.
- [x] Keep creation of accepted data, configuration, state, log, cache, and runtime roots.
- [x] Align comments and formatting with the resulting directory layout.
- [x] Review the file before continuing.

### 2. `src/spex/services/lock.py`

- [x] Restrict the lock to Hub application ownership.
- [x] Resolve `hub.lock` directly beneath the runtime directory.
- [x] Retain PID and process start time as lock metadata.
- [x] Remove session, child-role, and instance metadata.
- [x] Preserve advisory acquisition, complete writes, synchronization, and descriptor cleanup.
- [x] Align the class name, API, comments, and docstrings with its single purpose.
- [x] Review the file before continuing.

### 3. `src/spex/services/ipc_client.py`

- [x] Delete the generic IPC client rather than preserving an abstraction without demonstrated reuse.
- [x] Keep service-specific pipe handling with each spoke until stable duplication supports extraction.
- [x] Confirm no source file imports `ipc_client` or `ServiceClient`.
- [x] Review the removal before continuing.

### 4. `src/spex/services/live.py`

Complete. `LiveService(ServiceProcess)` implements only `_run_cycle()`; the pipe-accept, EOF-poll, `SIGTERM`/`SIGINT` handling, and pipe-close-on-exit all come from the shared base class, confirmed reviewed there.

- [x] Accept the child pipe endpoint through process construction.
- [x] Never send or receive an application message on it; the base class polls once per work cycle and treats EOF as a stop signal.
- [x] Rely on the shared `ServiceProcess` signal handler for operator-initiated stop; no control-message handling.
- [x] Drop the `paused` half of the state contract; the service is only running or stopped.
- [x] Close the pipe during every exit path.
- [x] Align comments and docstrings with scaffold behavior.
- [x] Review the file before continuing.

### 5. `src/spex/services/backfill.py`

Complete, same basis as step 4. `BackfillService(ServiceProcess)` is structurally identical to `LiveService`, only its `_run_cycle()` differs.

- [x] Apply the reviewed live-service control structure to backfill.
- [x] Drop the `paused` half of the state contract; the service is only running or stopped.
- [x] Close the pipe during every exit path.
- [x] Align comments and docstrings with scaffold behavior.
- [x] Review the file before continuing.

### 6. `src/spex/services/pipeline.py`

Complete, same basis as step 4.

- [x] Extract the shared worker process and pipe/signal stop lifecycle into `src/spex/services/service.py`, with the pipe used only for EOF-based Hub-loss detection.
- [x] Reduce live, backfill, and pipeline to concrete `ServiceProcess` subclasses.
- [x] Make the pipeline scaffold compatible with Hub-owned process and pipe supervision.
- [x] Preserve its validation-and-transformation responsibility.
- [x] Add only the lifecycle behavior required by the walking skeleton.
- [x] Review the files before continuing.

### 7. `src/spex/services/dashboard.py`

Reopened. `DashboardService` now subclasses `SpawnProcess` directly and accepts a pipe — a reversal of this step's original "no control-pipe behavior" target, since dashboard is grouped with the TUI now (long-lived, non-cyclic, stopped by `SIGTERM`/`SIGINT`) rather than with the EOF-polling workers. The pipe's purpose beyond that is not yet decided.

- [x] Subclass a spawnable `multiprocessing.Process` and accept the child pipe endpoint through construction.
- [ ] Install a `SIGTERM`/`SIGINT` handler that directly ends the dashboard (same shape as `SpexProcess`, not the workers' poll-and-flag pattern — there is no work cycle to poll between).
- [ ] Replace the `run()` stub (`pass`) with the dashboard's actual scaffold behavior.
- [ ] Decide and document what the pipe is for here, if anything beyond structural uniformity.
- [ ] Close the pipe during every exit path.
- [ ] Align comments and docstrings with scaffold behavior.
- [ ] Review the file before continuing.

### 8. `src/spex/services/hub.py`

- [x] Retain the explicit `spawn` context, Hub lock, process registry, and cleanup ownership.
- [x] Create one pipe pair before spawning each child.
- [x] Pass the child endpoint during spawn and close unused endpoint copies.
- [x] Store each parent endpoint with its role and process handle.
- [ ] Monitor every pipe endpoint and process sentinel without listener or handler threads. `run()` is currently a stub (`while True: pass` inside a `try`/`except`) — no monitoring happens yet; this is the pending async rewrite.
- [ ] Add the in-memory request ledger and synchronized request allocation needed by the walking skeleton. `_handle_message` now dispatches `start`/`stop` by calling `_spawn_service`/`_join_service`, but nothing calls `_handle_message` yet and there is no ledger at all. Defer the accepted/completed timeout criterion (`unknown` state, completion timeout, retry-timer restart) until a real situation demonstrates the need. Duplicate-ID idempotency depends on that same deferred retry path, so it is deferred with it; UUID message IDs keep accidental collision out of scope regardless. Keep only synchronized ID allocation for now.
- [x] Remove listener address, authentication key, listener lifecycle, and listener-shutdown messaging.
- [x] Preserve graceful join and forced-termination ownership.
- [ ] Review the file before continuing. `SERVICE_TYPES`/`ManagedService` including `tui` and `dashboard` is intentional — `_spawn_service` is the uniform spawn path for all five roles.

### 9. `src/spex/services/tui.py`

- [x] Keep the Textual application in the service package as a Hub-spawned child — `SpexProcess(SpawnProcess)` wraps `Spex` and is spawnable via `_spawn_service`.
- [ ] Accept the TUI child pipe endpoint. `SpexProcess.__init__` takes `pipe` structurally, but it is never passed to the `Spex` app itself and nothing reads or writes it — not functionally wired yet.
- [ ] Send operator intents as native dictionaries.
- [ ] Receive state through a background worker and cross Textual's thread-safe message boundary.
- [ ] Replace placeholder health behavior only when real Hub state is available.
- [ ] Preserve terminal ownership, bindings, and application-shutdown intent. Shutdown itself is no longer pipe-EOF-driven — `SpexProcess` needs a `SIGTERM`/`SIGINT` handler that calls `Spex.exit()` directly, the same shape as dashboard, since `app.run()` blocks with no cycle to poll from.
- [ ] Review the file before continuing.

### 10. `src/spex/__init__.py`

- [ ] Bootstrap the filesystem and start the Hub as the main process.
- [ ] Let the Hub create the Textual child and remaining service children.
- [ ] Preserve the bare `spex` entry point.
- [ ] Align the entry-point docstring with actual ownership.
- [ ] Review the file before continuing.

### 11. Obsolete transport removal

- [x] Delete the obsolete `src/spex/services/hub/ipc_listener.py` module with the nested Hub package.
- [x] Delete the obsolete generic client artifact.
- [ ] Remove `orjson` from control-plane imports while preserving any separate data-pipeline use.
- [ ] Confirm no code references listener addresses, authentication keys, hello messages, heartbeats, or runtime IPC paths.
- [ ] Review the removal before continuing.

### 12. Integration checkpoint

- [ ] Confirm every source module imports successfully.
- [ ] Confirm the Hub acquires the single runtime lock.
- [ ] Confirm the Hub spawns Textual and each walking-skeleton service with a dedicated pipe.
- [ ] Confirm native dictionary messages travel in both directions on the TUI's pipe.
- [ ] Confirm child exit is visible through sentinels for every child, and Hub loss is visible through pipe EOF for live, backfill, and pipeline, and through `SIGTERM`/`SIGINT` propagation for TUI and dashboard.
- [ ] Confirm application shutdown closes endpoints and joins every child.
- [ ] Reconcile completed work with `docs/TODO.md`, design documents, and `CHANGELOG.md`.
