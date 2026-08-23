# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Complete the thin walking-skeleton control plane before implementing Jetstream or data-pipeline behavior. Continue step 8 in `REFACTOR_TODO.md`, then proceed through the TUI and entry-point integration.

## Implemented structure

- The Hub runs in the main process under an explicit multiprocessing `spawn` context.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- Live, backfill, and pipeline inherit `ServiceProcess`, which owns the pipe-accept, EOF-poll, and `SIGTERM`/`SIGINT` handling for all three. Reviewed and confirmed correct this session.
- `SpexProcess` (tui.py) and `DashboardService` (dashboard.py) are their own `SpawnProcess` subclasses, not `ServiceProcess` — both are long-lived and non-cyclic, so they can't use the poll-a-flag-between-cycles pattern. Neither installs a signal handler. `DashboardService.run()` currently blocks in a placeholder sleep loop pending its real body in `docs/TODO.md` 0.7.
- The dashboard's pipe carries loss detection in both directions: the dashboard learns of Hub loss through pipe EOF, and the Hub learns of dashboard exit through the same endpoint and the process sentinel. It carries no application messages, and the placeholder `run()` does not read it yet.
- Every child receives a Hub-created duplex `multiprocessing.Pipe`. Only the TUI's is meant to carry messages, and that traffic isn't wired up yet (step 9). Live, backfill, and pipeline poll theirs once per work cycle purely to detect Hub loss through EOF; the TUI and dashboard don't poll their pipe at all.
- Pipe ownership supplies each child's identity; the TUI's control messages do not repeat session or instance identifiers.
- `_spawn_service` creates each child's pipe pair, passes the child endpoint, and closes the unused copy — confirmed working for all five roles (`live`, `backfill`, `pipeline`, `tui`, `dashboard`).
- The Hub's actual supervision loop (`run()`) is still a stub — it spawns the TUI, registers signal handlers, then sleeps until `self._running` clears, and joins. Nothing monitors pipes or sentinels yet, and `_handle_message` (which dispatches `start`/`stop`) has no caller. This is the pending `asyncio` rewrite.
- Live, backfill, and pipeline stop gracefully through `SIGTERM`/`SIGINT`, checked as a flag between cycles. The TUI exits normally through its own interface instead, and the Hub reads that child loss as its shutdown trigger. A `SIGTERM` handler calling `app.exit()` covers only the abnormal path and is tracked in `docs/TODO.md` 0.2, not this refactor. Dashboard needs no handler at all; termination without one is acceptable.
- `_join_service` closes the pipe, then `terminate()` and a fifteen-second wait if still alive, then `kill()`.

## Resume point

Continue [`src/spex/services/hub.py`](../src/spex/services/hub.py) with the real supervision loop — the confirmed `asyncio` rewrite. It is the last unchecked item in step 8, and the Hub review is complete, so step 9's TUI integration follows directly. No request ledger is needed: commands are one-off and fire-and-forget for the walking skeleton, and `_handle_message` already reflects that (dispatches `start`/`stop` directly, no response, no `message_id`). Full ledger design deferred in `process-control.md` until a correlated response is actually needed.

Hub review findings:

1. An unmatched message type still raises inside `_handle_message` (`case _: raise ValueError(...)`), carrying only the message type and no sender. Intentional: failures surface loudly rather than degrade, and the TUI is the only sender in the skeleton. Revisit when more children send messages.
2. `_join_service`'s terminate/kill escalation runs synchronously — once the real supervision loop exists, a slow-exiting child stalls supervision of every other service for the length of its escalation. Still open. The async rewrite must actually solve this with a task per escalation, not just replace the polling mechanism.
3. Async rewrite of `run()` — confirmed, not yet built. `run()` is `while self._running: time.sleep(0.1)` followed by `self._join()`. Open questions: task-exception visibility (asyncio silently drops exceptions from unreferenced tasks, which conflicts with (1)'s fail-fast stance) and the `__enter__`/`__exit__` shutdown lifecycle around an async `run()`. The real loop should use `loop.add_signal_handler()`; note that its callback runs on the event loop and cannot await, so teardown must stay outside it.
4. Resolved this session: the Hub's signal handler now only records the request by clearing `self._running`, and `run()` joins services after the loop exits. Teardown had been running inside the handler, where it blocks the main thread for each child's full escalation, can interrupt `_spawn_service` between `process.start()` and registry insertion (orphaning a live child), and cannot become a task under asyncio. Both handlers now follow the same rule: record intent, act on the main path.

Steps 1 through 7 in `REFACTOR_TODO.md` are complete. `pause`/`resume` are dropped entirely — a service is only running or stopped; operator-initiated stop is `process.terminate()` (`SIGTERM`) handled by the shared `ServiceProcess` handler; live, backfill, and pipeline keep their pipe only to detect Hub loss. Step 7 closed on the decision that the dashboard's pipe carries loss detection in both directions and no application messages.

Verified by test and worth remembering: `Connection.poll()` reports readability, not EOF specifically — it returns `True` for a waiting message exactly as it does for a closed peer. `ServiceProcess`'s bare `poll()` is therefore sound only while nothing is ever sent to those children. Any step that starts sending to live, backfill, or pipeline must replace it with a `recv()` treating `EOFError` as Hub loss and anything else as a message.

Considered and declined for now: pre-spawning every worker at Hub startup and gating actual work with `pause`/`resume` to keep them "hot," avoiding process-spawn latency on a TUI-issued `start`. `_spawn_service`/`_join_service`'s existing construct-and-start-together, join-and-discard-on-stop lifecycle stays. Revisit only if operator-perceived start latency proves noticeably slow in practice.

TUI and dashboard are long-lived, non-cyclic processes (`SpexProcess` blocks inside Textual's `app.run()`; dashboard has no bounded work cycle either), so neither uses the workers' pipe-EOF-poll pattern. The TUI exits through its own interface, and the Hub reads that child loss as its shutdown trigger. Verified this session: Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so while the TUI runs, Ctrl-C delivers a literal `\x03` byte to the TUI and no `SIGINT` to any process in the foreground group, including the Hub. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`. Exit through the interface is therefore the only normal shutdown path. Textual installs no `SIGTERM` or `SIGINT` handler of its own on this driver — only `SIGTSTP`, `SIGCONT`, `SIGWINCH`, and transiently `SIGTTOU`/`SIGTTIN`.

Remaining gap on the abnormal path: `Hub._join()` terminates every service including the TUI, so an external kill of the Hub or a supervisor exception sends the TUI an unhandled `SIGTERM` and leaves the terminal in raw mode with the alternate screen active. Tracked in `docs/TODO.md` 0.2 as TUI `SIGTERM` handling, by Joshua's decision that it is implementation rather than refactor scope. The same reasoning covers the PID-targeted-kill case, which orphans children because POSIX does not propagate a killed parent's signal.

Two open design threads, discussed but not decided:

1. A background thread blocked on `self._pipe.recv()` for TUI (and dashboard) would detect Hub loss without depending on any signal reaching the process — it fires on the OS closing the pipe regardless of cause, which also closes the abnormal-path and PID-targeted-kill gaps above. For the TUI this is not extra cost: it is the same background-worker thread step 9 already needs for real operator-intent/state traffic, so EOF detection comes free from the same `recv()` call. Textual requires crossing back to the main thread via `call_from_thread()`/`post_message()` to act on it, not calling `app.exit()` from that thread.
2. Once live/backfill/pipeline get real two-way messages, message handling likely needs its own thread there too: inline handling only checks the pipe between `_run_cycle()` calls, so a slow cycle delays response to anything arriving mid-cycle. This is close to `ServiceProcess`'s earlier shape (`_receive_thread` + `_send_lock`), removed only because there was nothing to receive yet. Bringing real messaging back likely means bringing at least the send lock back, since concurrent `.send()` calls on one `Connection` need serializing.

Scope decision, applied: `REFACTOR_TODO.md` covers control-plane mechanics only — process, pipe, and signal supervision. What a service does with its pipe is implementation and lives in `docs/TODO.md`. Step 9 is now the TUI transport wiring and its review; its operator intents, background-worker state receipt, real health indicator, and Textual-closure shutdown intent moved out, since `docs/TODO.md` 0.2 already covers all four. Step 12 keeps the mechanical confirmations and drops the bidirectional-message check as feature verification.

Remaining refactor sequence:

1. Build the Hub's `asyncio` supervision loop (step 8).
2. Pass a child pipe to the Textual service and wire it functionally (step 9).
3. Change the `spex` entry point to bootstrap and run the Hub as the main process (step 10).
4. Run step 12's integration checkpoint and reconcile `docs/TODO.md`, the design documents, and `CHANGELOG.md`.

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
- The changes described above are committed and pushed to the GitHub remote; the worktree is clean.

## Primary references

- [`docs/design/process-control.md`](design/process-control.md) defines the control-plane design.
- [`docs/design/architecture.md`](design/architecture.md) defines system boundaries and dependencies.
- [`docs/TODO.md`](TODO.md) defines the broader implementation roadmap.
- [`CHANGELOG.md`](../CHANGELOG.md) records confirmed project changes.
