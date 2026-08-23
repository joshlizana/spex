# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Complete the thin walking-skeleton control plane before implementing Jetstream or data-pipeline behavior. Continue step 8 in `REFACTOR_TODO.md`, then proceed through the TUI and entry-point integration.

## Implemented structure

- The Hub runs in the main process under an explicit multiprocessing `spawn` context.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- Live, backfill, and pipeline inherit `ServiceProcess`, which owns the pipe-accept, EOF-poll, and `SIGTERM`/`SIGINT` handling for all three. Reviewed and confirmed correct this session.
- `SpexProcess` (tui.py) and `DashboardService` (dashboard.py) are their own `SpawnProcess` subclasses, not `ServiceProcess` — both are long-lived and non-cyclic, so they can't use the poll-a-flag-between-cycles pattern. Neither has its `SIGTERM`/`SIGINT` handler wired up yet.
- Every child receives a Hub-created duplex `multiprocessing.Pipe`. Only the TUI's is meant to carry messages, and that traffic isn't wired up yet (step 9). Live, backfill, and pipeline poll theirs once per work cycle purely to detect Hub loss through EOF; the TUI and dashboard don't poll their pipe at all.
- Pipe ownership supplies each child's identity; the TUI's control messages do not repeat session or instance identifiers.
- `_spawn_service` creates each child's pipe pair, passes the child endpoint, and closes the unused copy — confirmed working for all five roles (`live`, `backfill`, `pipeline`, `tui`, `dashboard`).
- The Hub's actual supervision loop (`run()`) is still a stub — nothing monitors pipes or sentinels yet, and `_handle_message` (which dispatches `start`/`stop`) has no caller. This is the pending `asyncio` rewrite.
- Live, backfill, and pipeline stop gracefully through `SIGTERM`/`SIGINT`, checked as a flag between cycles. The TUI and dashboard are meant to stop through the same signals but acting directly (e.g. `app.exit()`) rather than a flag, since neither has a cycle to check one between — not yet implemented for either.
- `_join_service` closes the pipe, then `terminate()` and a fifteen-second wait if still alive, then `kill()`.

## Resume point

Continue [`src/spex/services/hub.py`](../src/spex/services/hub.py) with the real supervision loop — the confirmed `asyncio` rewrite. No request ledger is needed: commands are one-off and fire-and-forget for the walking skeleton, and `_handle_message` already reflects that (dispatches `start`/`stop` directly, no response, no `message_id`). Full ledger design deferred in `process-control.md` until a correlated response is actually needed. Complete the Hub review before modifying TUI integration.

Hub review findings, still open:

1. An unmatched message type still raises inside `_handle_message` (`case _: raise ValueError(...)`). Intentional for this stage — failures surface loudly rather than being handled defensively; revisit only when a real failure demonstrates a need for graceful handling. Currently unreachable in practice since nothing calls `_handle_message` yet.
2. `_join_service`'s terminate/kill escalation is written to run synchronously — once the real supervision loop exists, a slow-exiting child would stall supervision of every other service for the length of its escalation. Not yet reachable (the loop is a stub), but the async rewrite in (3) needs to actually solve this, not just replace the polling mechanism.
3. Async rewrite of `run()` — **confirmed**, no longer just a direction. Not yet built: `run()` is currently `while True: try: pass except KeyboardInterrupt: break except Exception: raise`, i.e. no `loop.add_reader()`, no task-per-escalation, nothing from the design discussion implemented yet. Open questions carried forward: task-exception visibility (asyncio silently drops exceptions from unreferenced tasks, which conflicts with (1)'s fail-fast stance) and the `__enter__`/`__exit__` shutdown lifecycle around an async `run()`. One new note: `signal.signal(signal.SIGINT, ...)` (already registered in `run()`) replaces Python's default `KeyboardInterrupt`-on-`SIGINT` behavior, so the stub's `except KeyboardInterrupt: break` is already dead code — the real loop should use `loop.add_signal_handler()`, not `except KeyboardInterrupt`.

Steps 4, 5, and 6 in `REFACTOR_TODO.md`, reopened earlier this session, are now complete: `pause`/`resume` are dropped entirely, a service is only running or stopped; operator-initiated stop moves from a pipe message to `process.terminate()` (`SIGTERM`), handled by the shared `ServiceProcess` handler; live, backfill, and pipeline keep their pipe only to detect Hub loss. Step 7 (dashboard) is now reopened instead — see `REFACTOR_TODO.md`'s "Resume here" for the current target across all of live/backfill/pipeline/TUI/dashboard and the per-file checklists.

Considered and declined for now: pre-spawning every worker at Hub startup and gating actual work with `pause`/`resume` to keep them "hot," avoiding process-spawn latency on a TUI-issued `start`. `_spawn`/`_join_service`'s existing construct-and-start-together, join-and-discard-on-stop lifecycle stays. Revisit only if operator-perceived start latency proves noticeably slow in practice — not before.

TUI and dashboard are long-lived, non-cyclic processes (`SpexProcess` blocks inside Textual's `app.run()`; dashboard has no bounded work cycle either), so they don't use the workers' pipe-EOF-poll pattern for Hub loss. They're expected to be ended by `SIGTERM`/`SIGINT` instead — the handler must directly command the app to exit (e.g. `app.exit()` for Textual), not set a flag polled between cycles, since there's no loop to poll from. Accepted gap: a kill targeting the Hub's specific PID (not its process group) orphans them with no signal ever arriving, since POSIX doesn't propagate a killed parent's signal to its children. Declined as out of scope — the only realistic path to a PID-targeted kill is Ctrl-C (which does reach them, sharing the Hub's process group) already having failed, at which point that failure is the bug to fix, not the orphan left behind.

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
