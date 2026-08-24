# Project Handoff

Status: active

This document provides the current working context for the next agent. [`AGENTS.md`](../AGENTS.md) defines the collaboration rules, and [`REFACTOR_TODO.md`](REFACTOR_TODO.md) remains the authoritative control-plane work sequence.

## Current objective

Continue the walking-skeleton application behavior on the verified direct-pipe control plane.

The ingestion service has exactly two phases: `replay` and `live`. The ATProto Python SDK's `atproto_jetstream.replay()` owns archive planning, decoding, cursor-based seam deduplication, and the transition to the WebSocket tail. Replay and live share one process, raw writer, durable cursor, and state artifact.

## Implemented structure

- Textual runs in the main process and owns the terminal, Hub process handle, and their direct pipe.
- The bare `spex` entry point bootstraps the filesystem and enters the context-managed Textual/Hub lifecycle.
- The Hub acquires the sole `hub.lock` and owns every child process handle.
- `IngestionService` and `PipelineService` inherit `ServiceProcess`, which owns their shared pipe, daemon EOF-monitor thread, and signal lifecycle.
- `Spex` owns the main-process Textual app and Hub child lifecycle. `DashboardService` is a long-lived `SpawnProcess`; both use daemon pipe-monitor threads. Hub EOF exits Textual through its thread-safe boundary, while dashboard EOF sets its shutdown flag.
- The dashboard's pipe carries loss detection in both directions: the dashboard learns of Hub loss through pipe EOF, and the Hub learns of dashboard exit through the same endpoint and the process sentinel. It carries no application messages.
- Every operational child receives a Hub-created duplex `multiprocessing.Pipe`; Textual creates its own pipe before spawning the Hub. Ingestion and processing send advisory telemetry but receive no commands under the target design; the current scaffolds have not implemented that telemetry yet.
- Pipe ownership supplies each child's identity; the TUI's control messages do not repeat session or instance identifiers.
- `_spawn_service` creates each operational child's pipe pair, passes the child endpoint, and closes the unused copy. The three Hub-owned roles are `ingest`, `pipeline`, and `dashboard`.
- The Hub's supervision loop (`run()`) is an `asyncio` loop. `loop.add_signal_handler` records shutdown intent without touching teardown. Each pass polls the TUI pipe and checks operational-service sentinels. TUI EOF ends the loop; worker loss is joined and dropped without stopping the Hub. Blocking joins run through `asyncio.to_thread`, and `_join` escalates all children concurrently with `asyncio.gather`. The Hub context completes cleanup before releasing the lock.
- Worker scaffolds stop gracefully through `SIGTERM`/`SIGINT`, checked as a flag between cycles. Textual exits through its interface, closes the Hub pipe, and joins the Hub. Dashboard needs no handler; termination without one is acceptable.
- `_join_service` closes the pipe, then `terminate()` and a fifteen-second wait if still alive, then `kill()`.

## Resume point

The control-plane refactor and integration checkpoint are complete. Continue in `docs/TODO.md` 0.2 with TUI operator intents, state exchange, real health, and the Hub-ready/error handshake. No request ledger is needed for the walking skeleton.

Hub review findings, all resolved this session except (1):

1. An unmatched message type raises inside `_handle_message` (`case _: raise ValueError(...)`), carrying only the message type and no sender. Intentional: failures surface loudly rather than degrade, and the TUI is the only sender in the skeleton. Revisit when more children send messages.
2. Resolved: `_join_service`'s blocking terminate/kill escalation no longer stalls supervision. `_join` runs every child's escalation through `asyncio.to_thread` under one `asyncio.gather`, so the five overlap, and `_handle_message`'s `stop` path threads its join the same way. The inline joins in the supervision loop act only on children whose sentinel already reports exit, so they return immediately.
3. Resolved: `run()` is the `asyncio` supervision loop. `loop.add_signal_handler` receives a plain method that only clears `self._running`, so no task is created and teardown stays on the main path after the loop exits. The lifecycle question settled on `__aenter__`/`__aexit__` — one event loop for the Hub's whole lifetime, with `__aexit__` awaiting `_join` before releasing the lock.
4. Resolved: the Hub's signal handler only records the request by clearing `self._running`, and `run()` joins services after the loop exits. Teardown had been running inside the handler, where it blocks the main thread for each child's full escalation, can interrupt `_spawn_service` between `process.start()` and registry insertion (orphaning a live child), and cannot become a task under asyncio. Both handlers follow the same rule: record intent, act on the main path.

Known and accepted in the Hub, not defects: `_spawn_service`'s `process.start()` blocks the loop for the duration of a `spawn` interpreter launch. `_join_service` is also not re-entrant — two concurrent calls for the same role would both pass the registry lookup and the second `del` would raise `KeyError`. Unreachable today, because `run()` is the only task on the loop and is suspended at the `await` while a threaded join runs. Revisit when step 9 introduces additional tasks.

Steps 1 through 8 in `REFACTOR_TODO.md` contain the completed direct-pipe work. `pause`/`resume` are dropped entirely — a service is only running or stopped; ingestion additionally reports `replay` or `live`. Operator-initiated stop is `process.terminate()` (`SIGTERM`) handled by the shared `ServiceProcess` handler. Step 7 closed on the decision that the dashboard's pipe carries loss detection in both directions and no application messages.

Verified by test and worth remembering: `Connection.poll()` reports readability, not EOF specifically. A worker's bare poll remains sound while the Hub sends it no messages; worker-to-Hub telemetry does not make the worker endpoint readable. The Hub must receive telemetry explicitly and treat `EOFError` as child loss.

Considered and declined for now: pre-spawning every worker at Hub startup and gating actual work with `pause`/`resume` to keep them "hot," avoiding process-spawn latency on a TUI-issued `start`. `_spawn_service`/`_join_service`'s existing construct-and-start-together, join-and-discard-on-stop lifecycle stays. Revisit only if operator-perceived start latency proves noticeably slow in practice.

TUI and dashboard are long-lived and non-cyclic, so both use pipe-monitor threads. Textual runs in the main process and exits through its interface; closing its pipe ends the Hub. Verified this session: Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so Ctrl-C delivers a literal `\x03` byte to Textual and no `SIGINT` to the foreground process group. Spex has no binding for that byte, so it is ignored. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`.

Remaining startup gap: the TUI-Hub protocol has no ready/error handshake. If the Hub fails before Textual enters its event loop, such as on lock contention, the TUI cannot yet report that failure deterministically. This remains in `docs/TODO.md` 0.2.

Worker pipe monitoring now runs from a daemon thread, so Hub loss is detected during a work cycle. A send lock remains unnecessary until telemetry introduces concurrent sends.

Scope decision, applied: `REFACTOR_TODO.md` covers control-plane mechanics only — process, pipe, and signal supervision. What a service does with its pipe is implementation and lives in `docs/TODO.md`. Step 9 is now the TUI transport wiring (9b) and its review (9c); its operator intents, background-worker state receipt, real health indicator, and Textual-closure shutdown intent moved out, since `docs/TODO.md` 0.2 already covers all four. Step 12 keeps the mechanical confirmations and drops the bidirectional-message check as feature verification.

The control-plane refactor sequence is complete.

## Confirmed boundaries

- Joshua owns all application behavior and implements review fixes.
- Agents own documentation, comments, docstrings, formatting, research, code review, and repository lifecycle.
- Small, targeted checks are authorized when proportionate. Ask Joshua before writing substantial throwaway scripts, broad test harnesses, or large test suites.
- Reviews address implemented scope and established failure boundaries without treating deferred features as current defects.
- The standard retry policy uses four delays: 1, 2, 4, and 8 seconds.
- Linux and WSL are the supported platforms.

## Verification status

- Source compilation succeeds with `python -m compileall -q src/spex`.
- All ten source modules import successfully under the project environment.
- A temporary-path lock probe acquires the Hub lock, rejects a concurrent owner, and releases it.
- Control-plane source contains no imports of the removed listener or generic IPC client.
- Full integration passes: the Hub starts all three operational services through TUI messages, stops and restarts pipeline, then closes and joins every child on TUI EOF with code zero. A real PTY `spex` run starts Textual in the main process and exits the complete application through `q` with code zero.

## Primary references

- [`docs/design/process-control.md`](design/process-control.md) defines the control-plane design.
- [`docs/design/architecture.md`](design/architecture.md) defines system boundaries and dependencies.
- [`docs/TODO.md`](TODO.md) defines the broader implementation roadmap.
- [`CHANGELOG.md`](../CHANGELOG.md) records confirmed project changes.
