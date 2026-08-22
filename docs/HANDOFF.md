# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Complete the thin walking-skeleton control plane before implementing Jetstream or data-pipeline behavior. Continue step 8 in `REFACTOR_TODO.md`, then proceed through the TUI and entry-point integration.

## Implemented structure

- The Hub runs in the main process under an explicit multiprocessing `spawn` context.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- Live ingestion, backfill, and pipeline workers inherit `ServiceProcess`. This is being reworked — see "Reopened this session" below.
- Every child receives a Hub-created duplex `multiprocessing.Pipe`. Only the TUI's ever carries a message; live, backfill, and pipeline poll theirs once per work cycle purely to detect Hub loss through EOF.
- The Hub and the TUI exchange native dictionaries through `Connection.send()` and `Connection.recv()`. No other child sends or receives a message.
- Pipe ownership supplies each child's identity; the TUI's control messages do not repeat session or instance identifiers.
- The Hub monitors every pipe endpoint and every child's process sentinel through `multiprocessing.connection.wait()`.
- TUI pipe EOF initiates its graceful shutdown. Live, backfill, and pipeline use the same EOF signal to detect an unexpected Hub loss, but their operator-initiated stop goes through a shared `ServiceProcess` `SIGTERM` handler instead, triggered by `process.terminate()`.
- Hub cleanup closes every pipe, joins with the standard 1-, 2-, 4-, and 8-second intervals, waits five seconds after termination, then kills and joins a process that remains alive.
- Textual lives in `src/spex/services/tui.py` and remains a placeholder launched directly by the entry point.
- Dashboard supervision remains a placeholder without worker-control IPC.

## Resume point

Continue [`src/spex/services/hub.py`](../src/spex/services/hub.py) with command dispatch and the in-memory request ledger. The concrete request-ID representation remains unresolved until this implementation requires it. Defer the accepted/completed timeout criterion (`unknown` state, completion timeout, "late acceptance restarts the timer") until a real situation demonstrates the need. Duplicate-ID idempotency depends on that same deferred retry path and is deferred with it; UUID message IDs keep accidental collision out of scope regardless. The ledger keeps only synchronized ID allocation for now. Complete the Hub review before modifying TUI integration.

Hub review findings from this session, still open:

1. An unmatched or invalid message from a child raises inside `_handle_message` and crashes `run()`. Intentional for this stage — failures surface loudly rather than being handled defensively; revisit only when a real failure demonstrates a need for graceful handling.
2. `_join_service`'s join/terminate/kill escalation runs synchronously inside `run()`'s single-threaded loop, so a slow-exiting child can stall supervision of every other service for the length of its escalation. Unlike (1), this is a present defect, not a deferred edge case.
3. Direction under discussion for (2): move `run()` from `connection.wait()` polling to an `asyncio` event loop, using `loop.add_reader()` per pipe/sentinel fd, with each departing service's escalation running as its own task instead of blocking the loop. Leaning this direction, not finalized. Open questions: task-exception visibility (asyncio silently drops exceptions from unreferenced tasks, which conflicts with (1)'s fail-fast stance) and the `__enter__`/`__exit__` shutdown lifecycle around an async `run()`. Revisit at implementation time.

Reopened this session — steps 4, 5, 6, and part of 8 in `REFACTOR_TODO.md`: `pause`/`resume` are dropped entirely; a service is only running or stopped. Operator-initiated stop moves from a pipe message to `process.terminate()` (`SIGTERM`), handled by a shared handler in `ServiceProcess` that ends the current work cycle gracefully. Live, backfill, and pipeline keep their pipe, but only to detect Hub loss — nothing is ever sent on it, a non-blocking `poll()` once per cycle is enough, no background thread needed. The TUI's pipe is the one carrying real two-way traffic, since it starts at launch rather than on operator command. See `REFACTOR_TODO.md`'s "Resume here" for the full target and the reopened per-file checklists.

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
