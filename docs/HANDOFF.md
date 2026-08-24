# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Complete the control-plane integration checkpoint on the consolidated ingestion architecture.

The ingestion service has exactly two phases: `replay` and `live`. The ATProto Python SDK's `atproto_jetstream.replay()` owns archive planning, decoding, cursor-based seam deduplication, and the transition to the WebSocket tail. Replay and live share one process, raw writer, durable cursor, and state artifact.

## Implemented structure

- The Hub runs in the main process under an explicit multiprocessing `spawn` context.
- The bare `spex` entry point bootstraps the filesystem, enters the Hub's async context, and runs supervision on one event loop.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- `IngestionService` and `PipelineService` inherit `ServiceProcess`, which owns their shared pipe, EOF-poll, and signal lifecycle.
- `SpexProcess` (tui.py) and `DashboardService` (dashboard.py) are their own `SpawnProcess` subclasses, not `ServiceProcess` — both are long-lived and non-cyclic, so they can't use the poll-a-flag-between-cycles pattern. The TUI monitors its pipe from a daemon thread and exits through Textual's thread-safe boundary on EOF. Neither installs a signal handler. `DashboardService.run()` currently blocks in a placeholder sleep loop pending its real body in `docs/TODO.md` 0.7.
- The dashboard's pipe carries loss detection in both directions: the dashboard learns of Hub loss through pipe EOF, and the Hub learns of dashboard exit through the same endpoint and the process sentinel. It carries no application messages, and the placeholder `run()` does not read it yet.
- Every child receives a Hub-created duplex `multiprocessing.Pipe`. The TUI's is meant to carry control traffic. Under the new target, ingestion and processing send advisory telemetry but receive no commands; the current scaffolds have not implemented that telemetry yet. Workers poll their pipe once per work cycle to detect Hub loss through EOF.
- Pipe ownership supplies each child's identity; the TUI's control messages do not repeat session or instance identifiers.
- `_spawn_service` creates each child's pipe pair, passes the child endpoint, and closes the unused copy. The four child roles are `ingest`, `pipeline`, `tui`, and `dashboard`.
- The Hub's supervision loop (`run()`) is an `asyncio` loop. `loop.add_signal_handler` records shutdown intent without touching teardown. Each pass branches on role: the TUI's pipe is polled and received, driving `_handle_message`; workers are checked by process sentinel only. TUI loss ends the loop through pipe EOF or a dead sentinel; worker loss is joined and dropped without stopping the Hub. Every blocking join runs through `asyncio.to_thread`, and `_join` escalates all children concurrently with `asyncio.gather`. The Hub is an async context manager (`__aenter__`/`__aexit__`), so `__aexit__` awaits `_join` before releasing the lock.
- Worker scaffolds stop gracefully through `SIGTERM`/`SIGINT`, checked as a flag between cycles. The TUI exits normally through its own interface instead, and the Hub reads that child loss as its shutdown trigger. A `SIGTERM` handler calling `app.exit()` covers only the abnormal path and is tracked in `docs/TODO.md` 0.2, not this refactor. Dashboard needs no handler at all; termination without one is acceptable.
- `_join_service` closes the pipe, then `terminate()` and a fifteen-second wait if still alive, then `kill()`.

## Resume point

Entry-point step 10 is complete. The bare `spex` command bootstraps the filesystem, then runs supervision inside `async with Hub()`, ensuring the Hub lock and child cleanup share the event-loop lifecycle. Continue at step 12's integration checkpoint. No request ledger is needed for the walking skeleton.

Hub review findings, all resolved this session except (1):

1. An unmatched message type raises inside `_handle_message` (`case _: raise ValueError(...)`), carrying only the message type and no sender. Intentional: failures surface loudly rather than degrade, and the TUI is the only sender in the skeleton. Revisit when more children send messages.
2. Resolved: `_join_service`'s blocking terminate/kill escalation no longer stalls supervision. `_join` runs every child's escalation through `asyncio.to_thread` under one `asyncio.gather`, so the five overlap, and `_handle_message`'s `stop` path threads its join the same way. The inline joins in the supervision loop act only on children whose sentinel already reports exit, so they return immediately.
3. Resolved: `run()` is the `asyncio` supervision loop. `loop.add_signal_handler` receives a plain method that only clears `self._running`, so no task is created and teardown stays on the main path after the loop exits. The lifecycle question settled on `__aenter__`/`__aexit__` — one event loop for the Hub's whole lifetime, with `__aexit__` awaiting `_join` before releasing the lock.
4. Resolved: the Hub's signal handler only records the request by clearing `self._running`, and `run()` joins services after the loop exits. Teardown had been running inside the handler, where it blocks the main thread for each child's full escalation, can interrupt `_spawn_service` between `process.start()` and registry insertion (orphaning a live child), and cannot become a task under asyncio. Both handlers follow the same rule: record intent, act on the main path.

Known and accepted in the Hub, not defects: `_spawn_service`'s `process.start()` blocks the loop for the duration of a `spawn` interpreter launch. `_join_service` is also not re-entrant — two concurrent calls for the same role would both pass the registry lookup and the second `del` would raise `KeyError`. Unreachable today, because `run()` is the only task on the loop and is suspended at the `await` while a threaded join runs. Revisit when step 9 introduces additional tasks.

Steps 1 through 8 in `REFACTOR_TODO.md` contain the completed direct-pipe work. `pause`/`resume` are dropped entirely — a service is only running or stopped; ingestion additionally reports `replay` or `live`. Operator-initiated stop is `process.terminate()` (`SIGTERM`) handled by the shared `ServiceProcess` handler. Step 7 closed on the decision that the dashboard's pipe carries loss detection in both directions and no application messages.

Verified by test and worth remembering: `Connection.poll()` reports readability, not EOF specifically. A worker's bare poll remains sound while the Hub sends it no messages; worker-to-Hub telemetry does not make the worker endpoint readable. The Hub must receive telemetry explicitly and treat `EOFError` as child loss.

Considered and declined for now: pre-spawning every worker at Hub startup and gating actual work with `pause`/`resume` to keep them "hot," avoiding process-spawn latency on a TUI-issued `start`. `_spawn_service`/`_join_service`'s existing construct-and-start-together, join-and-discard-on-stop lifecycle stays. Revisit only if operator-perceived start latency proves noticeably slow in practice.

TUI and dashboard are long-lived, non-cyclic processes (`SpexProcess` blocks inside Textual's `app.run()`; dashboard has no bounded work cycle either), so neither uses the workers' pipe-EOF-poll pattern. The TUI exits through its own interface, and the Hub reads that child loss as its shutdown trigger. Verified this session: Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so while the TUI runs, Ctrl-C delivers a literal `\x03` byte to the TUI and no `SIGINT` to any process in the foreground group, including the Hub. Spex has no binding for that byte, so it is ignored. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`. Exit through the interface is therefore the only normal shutdown path. Textual installs no `SIGTERM` or `SIGINT` handler of its own on this driver — only `SIGTSTP`, `SIGCONT`, `SIGWINCH`, and transiently `SIGTTOU`/`SIGTTIN`.

Remaining gap on the abnormal path: `Hub._join()` terminates every service including the TUI, so an external kill of the Hub or a supervisor exception sends the TUI an unhandled `SIGTERM` and leaves the terminal in raw mode with the alternate screen active. Tracked in `docs/TODO.md` 0.2 as TUI `SIGTERM` handling, by Joshua's decision that it is implementation rather than refactor scope. The same reasoning covers the PID-targeted-kill case, which orphans children because POSIX does not propagate a killed parent's signal.

One open design thread remains:

1. Once ingestion or processing gets real two-way messages, message handling likely needs its own thread there too: inline handling only checks the pipe between `_run_cycle()` calls, so a slow cycle delays response to anything arriving mid-cycle. This is close to `ServiceProcess`'s earlier shape (`_receive_thread` + `_send_lock`), removed only because there was nothing to receive yet. Bringing real messaging back likely means bringing at least the send lock back, since concurrent `.send()` calls on one `Connection` need serializing.

Scope decision, applied: `REFACTOR_TODO.md` covers control-plane mechanics only — process, pipe, and signal supervision. What a service does with its pipe is implementation and lives in `docs/TODO.md`. Step 9 is now the TUI transport wiring (9b) and its review (9c); its operator intents, background-worker state receipt, real health indicator, and Textual-closure shutdown intent moved out, since `docs/TODO.md` 0.2 already covers all four. Step 12 keeps the mechanical confirmations and drops the bidirectional-message check as feature verification.

Remaining refactor sequence:

1. Run step 12's integration checkpoint and reconcile `docs/TODO.md`, the design documents, and `CHANGELOG.md`.

## Confirmed boundaries

- Joshua owns all application behavior and implements review fixes.
- Agents own documentation, comments, docstrings, formatting, research, code review, and repository lifecycle.
- Small, targeted checks are authorized when proportionate. Ask Joshua before writing substantial throwaway scripts, broad test harnesses, or large test suites.
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
