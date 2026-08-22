# Control-plane refactor TODO

Status: active

This checklist replaces listener-based IPC with Hub-created duplex pipes while preserving a reviewable, file-at-a-time workflow. Joshua implements application behavior. Agents review each completed file and maintain its documentation, comments, and docstrings.

## Resume here

Steps 1 through 7 are complete. Step 8 has a reviewed process registry, Hub-owned pipe creation, sentinel and pipe monitoring, state handling, graceful pipe-loss shutdown, standard join intervals, and forced-exit escalation.

Continue step 8 with Hub command dispatch and the in-memory request ledger. Keep the concrete request-ID representation unresolved until that implementation requires it. Complete the remaining Hub review before starting the TUI integration in step 9.

## Confirmed target

- The Hub creates every child process and retains its process handle.
- The Hub creates one duplex `multiprocessing.Pipe` for each child and passes one endpoint during spawn.
- Processes exchange native Python dictionaries with `Connection.send()` and `Connection.recv()`.
- Pipe ownership supplies service identity. Messages contain `type`, `payload`, and a `message_id` only for correlated exchanges.
- Pipe EOF reports peer loss. Process sentinels report child exit. Command timeouts report unresponsive children.
- The Hub keeps request state in memory and discards it when the application session ends.
- Only the Hub acquires `hub.lock` directly beneath the `platformdirs` runtime directory.
- Process identity remains implicit in Hub-owned process handles and pipe endpoints.

## Working rule

Complete and review one numbered file step before beginning the next. Keep each intermediate step importable. Record an intentional temporary integration gap in this checklist when a later step must close it.

Guard expected architectural boundaries: pipe closure, child-process exit, partial resource acquisition, and failures crossing a thread boundary. Let ordinary programming errors surface naturally. Add narrower defensive handling when testing or observed failures establish a need.

Current integration gap: Hub command dispatch and its in-memory request ledger remain unimplemented.

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

- [x] Accept the child pipe endpoint through process construction.
- [x] Integrate control-message handling without adding live Jetstream behavior.
- [x] Preserve the walking-skeleton `running` and `paused` state contract.
- [x] Close the pipe during every exit path.
- [x] Align comments and docstrings with scaffold behavior.
- [x] Review the file before continuing.

### 5. `src/spex/services/backfill.py`

- [x] Apply the reviewed live-service control structure to backfill.
- [x] Preserve the walking-skeleton `running` and `paused` state contract.
- [x] Close the pipe during every exit path.
- [x] Align comments and docstrings with scaffold behavior.
- [x] Review the file before continuing.

### 6. `src/spex/services/pipeline.py`

- [x] Extract the shared worker process and pipe-control lifecycle into `src/spex/services/service.py`.
- [x] Reduce live, backfill, and pipeline to concrete `ServiceProcess` subclasses.
- [x] Make the pipeline scaffold compatible with Hub-owned process and pipe supervision.
- [x] Preserve its validation-and-transformation responsibility.
- [x] Add only the lifecycle behavior required by the walking skeleton.
- [x] Review the files before continuing.

### 7. `src/spex/services/dashboard.py`

- [x] Keep the dashboard scaffold compatible with external Hub process supervision.
- [x] Preserve its Streamlit-service responsibility.
- [x] Remove worker state, path setup, and control-pipe behavior that the dashboard does not use.
- [x] Add only the lifecycle behavior required by the walking skeleton.
- [x] Review the file before continuing.

### 8. `src/spex/services/hub.py`

- [x] Retain the explicit `spawn` context, Hub lock, process registry, and cleanup ownership.
- [x] Create one pipe pair before spawning each child.
- [x] Pass the child endpoint during spawn and close unused endpoint copies.
- [x] Store each parent endpoint with its role and process handle.
- [x] Monitor pipe endpoints and process sentinels without listener or handler threads.
- [ ] Add the in-memory request ledger and synchronized request allocation needed by the walking skeleton.
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
