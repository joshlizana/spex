# Control-plane refactor TODO

Status: active

This checklist replaces listener-based IPC with Hub-created duplex pipes while preserving a reviewable, file-at-a-time workflow. Joshua implements application behavior. Agents review each completed file and maintain its documentation, comments, and docstrings.

## Resume here

Steps 1 through 3 and 7 are complete and stand. Steps 4, 5, 6, and part of 8 are reopened: their checklists assumed a Hub-owned pipe on every child, and that assumption no longer holds (see below).

New target for live, backfill, and pipeline: drop `pause`/`resume` entirely, a service is only running or stopped. `start` stays spawn-only. Operator-initiated `stop` moves to `process.terminate()` (`SIGTERM`) — `ServiceProcess` installs a shared handler so the current work cycle ends gracefully; each subclass still only differs in its unit of work per cycle. Each of the three still receives a Hub-owned pipe, but only to detect Hub loss: nothing is ever sent on it, and a non-blocking `poll()` once per work cycle (no background thread) is enough to notice EOF and stop the same way `SIGTERM` does. The TUI child (step 9) is the one genuine two-way exception — it is the service started at launch rather than on operator command, and its pipe carries real operator-intent/state traffic.

Continue step 8 with Hub command dispatch and the in-memory request ledger. Keep the concrete request-ID representation unresolved until that implementation requires it. Complete the remaining Hub review before starting the TUI integration in step 9.

## Confirmed target

- The Hub creates every child process and retains its process handle.
- The Hub creates a duplex `multiprocessing.Pipe` for every child and passes one endpoint during spawn.
- The Hub and the TUI exchange native Python dictionaries with `Connection.send()` and `Connection.recv()`. Live, backfill, and pipeline never send or receive a message on theirs.
- Pipe ownership supplies service identity for every child. Messages contain `type`, `payload`, and a `message_id` only for correlated exchanges — only the TUI ever sends one.
- Pipe EOF reports peer loss for every child. For live, backfill, and pipeline it is the only signal of Hub loss, checked with a non-blocking `poll()` once per work cycle. Process sentinels report every child's exit. Command timeouts report an unresponsive TUI.
- Live, backfill, and pipeline stop, when the Hub is alive and initiates it, through a shared `ServiceProcess` `SIGTERM` handler that ends the current work cycle gracefully; the Hub triggers it with `process.terminate()`, not a pipe message.
- The Hub keeps request state in memory and discards it when the application session ends.
- Only the Hub acquires `hub.lock` directly beneath the `platformdirs` runtime directory.
- Process identity remains implicit in Hub-owned process handles and pipe endpoints.

## Working rule

Complete and review one numbered file step before beginning the next. Keep each intermediate step importable. Record an intentional temporary integration gap in this checklist when a later step must close it.

Guard expected architectural boundaries: pipe closure, child-process exit, partial resource acquisition, and failures crossing a thread boundary. Let ordinary programming errors surface naturally. Add narrower defensive handling when testing or observed failures establish a need. This includes timeout and retry criteria: defer them until an observed failure demonstrates the need, and let an unmatched or malformed internal message crash the Hub during this stage rather than degrade gracefully.

Current integration gap: Hub command dispatch and its in-memory request ledger remain unimplemented. Steps 4, 5, and 6 below predate the decision to drop pause/resume and reduce live, backfill, and pipeline's pipe to EOF-only Hub-loss detection; their checklists need reconciling with the new target above before those files are touched again. Step 8's pipe items need the same reconciling — every child gets a pipe again, but only the TUI's ever carries a message.

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

Reopened. This checklist predates dropping pause/resume and reducing this service's pipe to EOF-only Hub-loss detection — see the new target under "Resume here."

- [ ] Accept the child pipe endpoint through process construction, as before.
- [ ] Never send or receive an application message on it; poll it once per work cycle and treat EOF as a stop signal.
- [ ] Rely on the shared `ServiceProcess` `SIGTERM` handler for operator-initiated stop; drop control-message handling entirely.
- [ ] Drop the `paused` half of the state contract; the service is only running or stopped.
- [ ] Close the pipe during every exit path.
- [ ] Align comments and docstrings with scaffold behavior.
- [ ] Review the file before continuing.

### 5. `src/spex/services/backfill.py`

Reopened, same basis as step 4.

- [ ] Apply the reviewed live-service control structure to backfill.
- [ ] Drop the `paused` half of the state contract; the service is only running or stopped.
- [ ] Close the pipe during every exit path.
- [ ] Align comments and docstrings with scaffold behavior.
- [ ] Review the file before continuing.

### 6. `src/spex/services/pipeline.py`

Reopened, same basis as step 4.

- [ ] Extract the shared worker process and pipe/`SIGTERM` stop lifecycle into `src/spex/services/service.py`, with the pipe used only for EOF-based Hub-loss detection.
- [x] Reduce live, backfill, and pipeline to concrete `ServiceProcess` subclasses.
- [ ] Make the pipeline scaffold compatible with Hub-owned process and pipe supervision.
- [x] Preserve its validation-and-transformation responsibility.
- [x] Add only the lifecycle behavior required by the walking skeleton.
- [ ] Review the files before continuing.

### 7. `src/spex/services/dashboard.py`

- [x] Keep the dashboard scaffold compatible with external Hub process supervision.
- [x] Preserve its Streamlit-service responsibility.
- [x] Remove worker state, path setup, and control-pipe behavior that the dashboard does not use.
- [x] Add only the lifecycle behavior required by the walking skeleton.
- [x] Review the file before continuing.

### 8. `src/spex/services/hub.py`

- [x] Retain the explicit `spawn` context, Hub lock, process registry, and cleanup ownership.
- [ ] Create one pipe pair before spawning each child.
- [ ] Pass the child endpoint during spawn and close unused endpoint copies.
- [ ] Store each parent endpoint with its role and process handle.
- [ ] Monitor every pipe endpoint and process sentinel without listener or handler threads. Only the TUI's pipe ever carries a message; live, backfill, and pipeline's are polled for EOF alone.
- [ ] Add the in-memory request ledger and synchronized request allocation needed by the walking skeleton. Defer the accepted/completed timeout criterion (`unknown` state, completion timeout, retry-timer restart) until a real situation demonstrates the need. Duplicate-ID idempotency depends on that same deferred retry path, so it is deferred with it; UUID message IDs keep accidental collision out of scope regardless. Keep only synchronized ID allocation for now.
- [x] Remove listener address, authentication key, listener lifecycle, and listener-shutdown messaging.
- [x] Preserve graceful join and forced-termination ownership.
- [ ] Review the file before continuing.

### 9. `src/spex/services/tui.py`

- [ ] Keep the Textual application in the service package as a Hub-spawned child.
- [ ] Accept the TUI child pipe endpoint.
- [ ] Send operator intents as native dictionaries.
- [ ] Receive state through a background worker and cross Textual's thread-safe message boundary.
- [ ] Replace placeholder health behavior only when real Hub state is available.
- [ ] Preserve terminal ownership, bindings, and application-shutdown intent.
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
- [ ] Confirm native dictionary messages travel in both directions.
- [ ] Confirm child exit and Hub loss are visible through sentinels or pipe EOF.
- [ ] Confirm application shutdown closes endpoints and joins every child.
- [ ] Reconcile completed work with `docs/TODO.md`, design documents, and `CHANGELOG.md`.
