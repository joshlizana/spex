# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Complete the thin walking-skeleton control plane before implementing Jetstream or data-pipeline behavior. Continue step 8 in `REFACTOR_TODO.md`, then proceed through the TUI and entry-point integration.

## Implemented structure

- The Hub runs in the main process under an explicit multiprocessing `spawn` context.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- Live ingestion, backfill, and pipeline workers inherit `ServiceProcess`.
- Each worker receives one endpoint of a Hub-created duplex `multiprocessing.Pipe`.
- Workers exchange native dictionaries through `Connection.send()` and `Connection.recv()`.
- Pipe ownership supplies role identity; control messages do not repeat session or instance identifiers.
- The Hub monitors pipe endpoints and process sentinels through `multiprocessing.connection.wait()`.
- Pipe EOF initiates graceful worker shutdown.
- Hub cleanup closes the pipe, joins with the standard 1-, 2-, 4-, and 8-second intervals, waits five seconds after termination, then kills and joins a process that remains alive.
- Textual lives in `src/spex/services/tui.py` and remains a placeholder launched directly by the entry point.
- Dashboard supervision remains a placeholder without worker-control IPC.

## Resume point

Continue [`src/spex/services/hub.py`](../src/spex/services/hub.py) with command dispatch and the in-memory request ledger. The concrete request-ID representation remains unresolved until this implementation requires it. Complete the Hub review before modifying TUI integration.

After step 8:

1. Pass a child pipe to the Textual service.
2. Send operator intents from Textual as native dictionaries.
3. Receive Hub state in a background worker and cross Textual's thread-safe messaging boundary.
4. Replace the random health indicator only when real Hub state is available.
5. Change the `spex` entry point to bootstrap and run the Hub as the main process.

## Confirmed boundaries

- Joshua owns all application behavior and implements review fixes.
- Agents own documentation, comments, docstrings, formatting, research, code review, and repository lifecycle.
- Tests run only when Joshua requests them.
- Reviews address implemented scope and established failure boundaries without treating deferred features as current defects.
- The standard retry policy uses four delays: 1, 2, 4, and 8 seconds.
- Linux and WSL are the supported platforms.

## Verification status

- Source compilation succeeds with `python -m compileall -q src/spex`.
- Control-plane source contains no imports of the removed listener or generic IPC client.
- Behavioral multiprocessing, IPC, shutdown, and Textual integration tests remain pending.
- The worktree is clean at the start of this handoff update.

## Primary references

- [`docs/design/process-control.md`](design/process-control.md) defines the control-plane design.
- [`docs/design/architecture.md`](design/architecture.md) defines system boundaries and dependencies.
- [`docs/TODO.md`](TODO.md) defines the broader implementation roadmap.
- [`CHANGELOG.md`](../CHANGELOG.md) records confirmed project changes.
