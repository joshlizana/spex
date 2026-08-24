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
- Pipe ownership supplies each child's identity. The TUI sends no service-lifecycle messages; the Hub sends readiness and aggregated service state upward through their dedicated pipe.
- `_spawn_service` creates each operational child's pipe pair, passes the child endpoint, and closes the unused copy. The three Hub-owned roles are `ingest`, `pipeline`, and `dashboard`.
- The Hub's supervision loop (`run()`) is an `asyncio` loop. `loop.add_signal_handler` records shutdown intent without touching teardown. Each pass polls the TUI pipe and checks operational-service sentinels. TUI EOF ends the loop; worker loss is joined and dropped without stopping the Hub. Blocking joins run through `asyncio.to_thread`, and `_join` escalates all children concurrently with `asyncio.gather`. The Hub context completes cleanup before releasing the lock.
- Worker scaffolds stop gracefully through `SIGTERM`/`SIGINT`, checked as a flag between cycles. Textual exits through its interface, closes the Hub pipe, and joins the Hub. Dashboard needs no handler; termination without one is acceptable.
- `_join_service` closes the pipe, then `terminate()` and a fifteen-second wait if still alive, then `kill()`.

## Resume point

The control-plane refactor and integration checkpoint are complete. Joshua has decided that every operational service starts with the Hub and the TUI exposes no service-lifecycle controls. Continue in `docs/TODO.md` 0.2 with state exchange and real health. No request ledger is needed.

Hub review findings are resolved. `_join_service`'s blocking terminate/kill escalation runs through `asyncio.to_thread`, and `_join` overlaps every child's escalation under one `asyncio.gather`. `run()` owns supervision on one event loop; signal handlers only record shutdown intent, and the Hub context completes child cleanup before releasing the lock.

Known and accepted in the Hub, not defects: `_spawn_service`'s `process.start()` blocks the loop for the duration of a `spawn` interpreter launch. `_join_service` is also not re-entrant — two concurrent calls for the same role would both pass the registry lookup and the second `del` would raise `KeyError`. Unreachable today, because `run()` is the only task on the loop and is suspended at the `await` while a threaded join runs. Revisit when step 9 introduces additional tasks.

Steps 1 through 8 in `REFACTOR_TODO.md` contain the completed direct-pipe work. `pause`/`resume` and individual service controls are dropped entirely. Every operational service starts with the Hub and stops during application shutdown; ingestion additionally reports `replay` or `live`.

Verified by test and worth remembering: `Connection.poll()` reports readability, not EOF specifically. A worker's bare poll remains sound while the Hub sends it no messages; worker-to-Hub telemetry does not make the worker endpoint readable. The Hub must receive telemetry explicitly and treat `EOFError` as child loss.

The Hub starts ingestion, pipeline, and dashboard while entering its lock-and-cleanup context, then reports `ready` to Textual. Partial startup failure joins every child already registered and releases the Hub lock before propagating an error. The next implementation step removes the transitional `start` and `stop` handler, drains worker telemetry, and forwards aggregated state to Textual. Textual provides configuration and operational visibility without start, stop, pause, resume, or manual-restart controls.

TUI and dashboard are long-lived and non-cyclic, so both use pipe-monitor threads. Textual runs in the main process and exits through its interface; closing its pipe ends the Hub. Verified this session: Textual's Linux driver clears the `ISIG` termios flag by default (`drivers/linux_driver.py`, Textual 8.2.8), so Ctrl-C delivers a literal `\x03` byte to Textual and no `SIGINT` to the foreground process group. Spex has no binding for that byte, so it is ignored. `TEXTUAL_ALLOW_SIGNALS` restores `ISIG`.

The TUI waits for the Hub's first `ready` or `error` message before starting its pipe-monitor thread or entering Textual. Lock contention, configuration loading, and operational-service startup all occur before `ready`; failure returns a deterministic startup error. Handshake failure also stops and joins the Hub and closes the parent pipe. The current `ready` message carries no protocol version or service snapshot, so the complete readiness payload remains with the state-exchange work.

Worker pipe monitoring now runs from a daemon thread, so Hub loss is detected during a work cycle. A send lock remains unnecessary until telemetry introduces concurrent sends.

Scope decision, applied: `REFACTOR_TODO.md` covers control-plane mechanics only. Automatic service startup, background state receipt, the real health indicator, and the startup handshake live in `docs/TODO.md`.

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
- Control-plane integration passes for the implemented transport scaffold and shutdown lifecycle. Joshua verified that a real `spex` run starts all operational services and exits through `q` with code zero and no Spex process left behind. Source compilation and whitespace validation pass with automatic startup.
- The managed Codex sandbox rejects local `socket.send()` with `EPERM`, which prevents asyncio's cross-thread self-pipe wakeup and makes `asyncio.to_thread()` checks hang after their functions return. Run Hub integration checks with approved unsandboxed execution; normal Linux and WSL runs do not exhibit this sandbox behavior.

## Primary references

- [`docs/design/process-control.md`](design/process-control.md) defines the control-plane design.
- [`docs/design/architecture.md`](design/architecture.md) defines system boundaries and dependencies.
- [`docs/TODO.md`](TODO.md) defines the broader implementation roadmap.
- [`CHANGELOG.md`](../CHANGELOG.md) records confirmed project changes.
