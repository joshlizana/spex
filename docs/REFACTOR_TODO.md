# Control-plane refactor TODO

Status: active

This checklist replaces listener-based IPC with Hub-created duplex pipes while preserving a reviewable, file-at-a-time workflow. Joshua implements application behavior. Agents review each completed file and maintain its documentation, comments, and docstrings.

## Resume here

Steps 1 through 7 are complete and stand. Step 8 is partly done; step 9 is partly done — see each section below.

Target for live, backfill, and pipeline, now implemented: drop `pause`/`resume` entirely, a service is only running or stopped. `start` stays spawn-only. Operator-initiated `stop` moves to `process.terminate()` (`SIGTERM`) — `ServiceProcess` installs a shared handler so the current work cycle ends gracefully; each subclass still only differs in its unit of work per cycle. Each of the three still receives a Hub-owned pipe, but only to detect Hub loss: nothing is ever sent on it, and a non-blocking `poll()` once per work cycle (no background thread) is enough to notice EOF and stop the same way `SIGTERM` does.

TUI and dashboard don't fit that pattern — both are long-lived and non-cyclic (TUI blocks inside Textual's `app.run()`; dashboard has no bounded work cycle either), so neither can poll a pipe between cycles. The TUI exits through its own interface, and the Hub reads that child loss as its shutdown trigger. A `SIGTERM` handler calling `Spex.exit()` covers only the abnormal path — an external kill of the Hub or a supervisor exception, where `_join()` would otherwise terminate the TUI unhandled and leave the terminal in raw mode — and is tracked in `docs/TODO.md` 0.2 as implementation rather than refactor scope. The TUI is still the one genuine two-way exception for messaging: it is the service started at launch rather than on operator command, and its pipe is meant to carry real operator-intent/state traffic once step 9 finishes.

Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so while the TUI runs, Ctrl-C delivers a literal `\x03` byte to the TUI and no `SIGINT` to any process in the foreground group, including the Hub. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`. Exit through the TUI interface is therefore the only normal shutdown path.

Continue step 8 with the real supervision loop (the confirmed `asyncio` rewrite), the last unchecked item in that step. No request ledger is needed — commands are one-off and fire-and-forget for the walking skeleton; that whole design is deferred in `process-control.md` until a correlated response is actually needed. The Hub review is complete, so step 9's TUI integration follows directly.

## Confirmed target

- The Hub creates every child process and retains its process handle.
- The Hub creates a duplex `multiprocessing.Pipe` for every child and passes one endpoint during spawn.
- The Hub and the TUI exchange native Python dictionaries with `Connection.send()` and `Connection.recv()`. Live, backfill, pipeline, and dashboard never send or receive a message on theirs.
- Pipe ownership supplies service identity for every child. Messages contain `type`, `payload`, and a `message_id` only for correlated exchanges — only the TUI ever sends one.
- Pipe EOF is the only signal of Hub loss for live, backfill, and pipeline, checked with a non-blocking `poll()` once per work cycle. It also serves the dashboard. It plays no role in stopping the TUI, which exits through its interface. Process sentinels report every child's exit regardless.
- `poll()` reports readability, not EOF specifically: it returns `True` for a waiting message just as it does for a closed peer, verified by test. This is sound only while nothing is ever sent to these children. Any step that starts sending to live, backfill, or pipeline must replace the bare `poll()` with a `recv()` that treats `EOFError` as Hub loss and anything else as a message.
- Live, backfill, and pipeline stop, when the Hub is alive and initiates it, through a shared `ServiceProcess` `SIGTERM` handler that ends the current work cycle gracefully; the Hub triggers it with `process.terminate()`, not a pipe message.
- The TUI stops by exiting through its own interface; the Hub detects that child loss and shuts down. The dashboard stops through `SIGTERM`/`SIGINT` without a handler, since it holds no in-flight state.
- No request state is kept — commands are one-off and fire-and-forget, nothing to track or discard.
- Only the Hub acquires `hub.lock` directly beneath the `platformdirs` runtime directory.
- Process identity remains implicit in Hub-owned process handles and pipe endpoints.

## Working rule

Complete and review one numbered file step before beginning the next. Keep each intermediate step importable. Record an intentional temporary integration gap in this checklist when a later step must close it.

Guard expected architectural boundaries: pipe closure, child-process exit, partial resource acquisition, and failures crossing a thread boundary. Let ordinary programming errors surface naturally. Add narrower defensive handling when testing or observed failures establish a need. This includes timeout and retry criteria: defer them until an observed failure demonstrates the need, and let an unmatched or malformed internal message crash the Hub during this stage rather than degrade gracefully.

Current integration gap: Hub's supervision loop remains unimplemented — `run()` is a stub pending the confirmed `asyncio` rewrite. `_handle_message` exists and dispatches `start`/`stop`, but nothing calls it yet. No ledger gap — none is needed.

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

Complete. `DashboardService` now subclasses `SpawnProcess` directly and accepts a pipe — a reversal of this step's original "no control-pipe behavior" target. No signal handling needed: dashboard is read-only display with no in-flight state, so an unhandled `SIGTERM`/`SIGINT`/immediate exit is acceptable, and its underlying framework may already handle signals on its own. Its actual scaffold behavior (`run()`'s real body) is `docs/TODO.md` 0.7 territory, not refactor scope — this checklist only covers whether it fits the Hub's process/pipe supervision model.

- [x] Subclass a spawnable `multiprocessing.Process` and accept the child pipe endpoint through construction.
- [x] The pipe carries loss detection in both directions: the dashboard learns of Hub loss through pipe EOF, and the Hub learns of dashboard exit through the same endpoint and the process sentinel. It carries no application messages.
- [x] Close the pipe during every exit path.
- [x] Align comments and docstrings with scaffold behavior.
- [x] Review the file before continuing.

Open implementation gap, tracked in `docs/TODO.md` 0.7 rather than here: `run()` currently blocks in a placeholder sleep loop and never reads the pipe, so Hub loss is not yet detected. The real dashboard body has to consult the pipe for EOF.

### 8. `src/spex/services/hub.py`

- [x] Retain the explicit `spawn` context, Hub lock, process registry, and cleanup ownership.
- [x] Create one pipe pair before spawning each child.
- [x] Pass the child endpoint during spawn and close unused endpoint copies.
- [x] Store each parent endpoint with its role and process handle.
- [ ] Monitor every pipe endpoint and process sentinel without listener or handler threads. `run()` is currently a stub (`while True: pass` inside a `try`/`except`) — no monitoring happens yet; this is the pending async rewrite.
- [x] No request ledger needed — the walking skeleton only sends one-off, fire-and-forget commands. `_handle_message` dispatches `start`/`stop` straight to `_spawn_service`/`_join_service` with no response and no `message_id` in use anywhere; nothing to track. Full ledger design deferred in `process-control.md` until a correlated response is actually needed.
- [x] Remove listener address, authentication key, listener lifecycle, and listener-shutdown messaging.
- [x] Preserve graceful join and forced-termination ownership.
- [x] Review the file before continuing. `SERVICE_TYPES`/`ManagedService` including `tui` and `dashboard` is intentional — `_spawn_service` is the uniform spawn path for all five roles.

### 9. `src/spex/services/tui.py`

- [x] Keep the Textual application in the service package as a Hub-spawned child — `SpexProcess(SpawnProcess)` wraps `Spex` and is spawnable via `_spawn_service`.
- [ ] Accept the TUI child pipe endpoint. `SpexProcess.__init__` takes `pipe` structurally, but it is never passed to the `Spex` app itself and nothing reads or writes it — not functionally wired yet.
- [ ] Send operator intents as native dictionaries.
- [ ] Receive state through a background worker and cross Textual's thread-safe message boundary.
- [ ] Replace placeholder health behavior only when real Hub state is available.
- [ ] Preserve terminal ownership, bindings, and application-shutdown intent. Normal shutdown runs through the TUI interface, with the Hub reading the resulting child loss; the abnormal-path `SIGTERM` handler is tracked in `docs/TODO.md` 0.2.
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
- [x] Confirm `orjson` is absent from control-plane transport. Its only use is `src/spex/services/lock.py`, writing lock metadata, which is not transport.
- [x] Confirm no code references listener addresses, authentication keys, hello messages, heartbeats, or runtime IPC paths.
- [x] Review the removal before continuing.

### 12. Integration checkpoint

- [ ] Confirm every source module imports successfully.
- [ ] Confirm the Hub acquires the single runtime lock.
- [ ] Confirm the Hub spawns Textual and each walking-skeleton service with a dedicated pipe.
- [ ] Confirm native dictionary messages travel in both directions on the TUI's pipe.
- [ ] Confirm child exit is visible through sentinels for every child, and Hub loss is visible through pipe EOF for live, backfill, and pipeline, and through `SIGTERM`/`SIGINT` propagation for TUI and dashboard.
- [ ] Confirm application shutdown closes endpoints and joins every child.
- [ ] Reconcile completed work with `docs/TODO.md`, design documents, and `CHANGELOG.md`.
