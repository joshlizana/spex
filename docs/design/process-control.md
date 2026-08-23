# Process Control

Status: proposed

This document defines application sessions, worker identity, IPC, supervision, locks, request tracking, and shutdown behavior.

## Ownership

The `spex` console entry point launches a dedicated main-process orchestrator. It owns the application session, child lifecycles, control pipes, control messages, configuration, credentials, request state, logging, and aggregate health. Textual and every application service communicates only with this Hub for control.

The orchestrator creates Textual and every named service child with `multiprocessing.Process` under one explicit `spawn` context and retains each direct process handle. All application process spawning uses multiprocessing. Pool executors remain outside application orchestration.

The orchestrator creates one duplex control pipe before spawning each child and passes one endpoint to it, retaining the other under its known role and process handle. Inside the TUI process, connection reads cross Textual's thread-safe `post_message()` or `call_from_thread()` boundary and never mutate Textual objects from a connection thread. Textual actions send operator intents to the orchestrator through this pipe.

Live, backfill, and pipeline never exchange a message on their pipe. Its only purpose for these three is detecting Hub loss through EOF; the orchestrator otherwise tracks each as running or stopped from its own process registry and stops one directly with `process.terminate()`.

The TUI and the dashboard are long-lived processes with no bounded work cycle — the TUI blocks inside Textual's own event loop, and the dashboard has no cycle either. Neither can poll its pipe between cycles the way the three workers do, so neither uses the workers' poll-a-flag pattern. The TUI needs an explicit `SIGTERM`/`SIGINT` handler that commands the app to exit directly, since it owns the terminal and an unhandled kill would leave it in a bad state. The dashboard needs none — it is read-only display with no in-flight state to protect, so an unhandled signal or immediate exit is acceptable, and its underlying framework may already handle signals on its own. The dashboard's pipe currently has no confirmed purpose beyond structural uniformity.

## Resource ownership

Components keep resources local until initialization succeeds. A component that acquires several resources uses an `ExitStack` to clean up partial initialization and transfers that stack to the long-lived owner after successful setup. Shutdown releases owned resources in reverse acquisition order.

Individual files and pipe connections use their context-manager interfaces directly. Components with one straightforward resource remain direct context managers and do not require an `ExitStack`.

## Walking-skeleton service state

M0 represents each worker (live, backfill, pipeline) with one field: `running`. There is no paused state; a worker is either running or stopped.

A newly spawned worker starts running. The Hub spawns a worker in response to an operator start action, so startup begins work directly. The Hub stops a worker with `process.terminate()` (`SIGTERM`). A shared `ServiceProcess` handler catches the signal and ends the worker's current work cycle gracefully before exit.

## Process identity

The Hub identifies each service through the role, process handle, and pipe endpoint stored in its process registry. Session and instance identifiers remain outside the walking-skeleton control contract.

## IPC transport

The orchestrator creates a dedicated `multiprocessing.Pipe(duplex=True)` for each child from the application `spawn` context. The orchestrator and child close their unused endpoint copies after spawning. EOF identifies peer loss. A restarted child receives a new pipe.

The Hub retains each parent endpoint under the role and process handle it launched, so the pipe establishes transport identity without endpoint discovery or authentication. The Hub and the TUI exchange native Python dictionaries through `Connection.send()` and `Connection.recv()`. These methods use pickle and remain restricted to inherited pipes between Hub-created processes. Live, backfill, and pipeline never send or receive a message on their pipe — its only purpose is detecting Hub loss through EOF. Each of these workers checks it with a non-blocking `poll()` once per work cycle; no background thread is needed, since nothing else ever uses the connection.

Every message contains a `type` and `payload`. A message includes a `message_id` when it belongs to a request-response exchange. Role identity remains connection context rather than a repeated message field. The initial state reports the protocol version once during readiness.

## Child readiness

The TUI's first message carries its initial state and protocol version. The orchestrator associates it with the role and process handle recorded when launching it.

The TUI becomes ready after the Hub accepts its initial state. Pipe creation and transfer occur as part of process creation and have no connection retry or hello acknowledgment.

Acknowledgment message types use the `<type>_ack` naming convention. An acknowledgment confirms receipt or protocol acceptance and does not represent completion of an asynchronous operation.

State exchange uses two message types. `state_request` asks the Hub for current state. `state` carries either one service update or a complete service snapshot, with its payload identifying the included scope.

Service-control message types use the concise names `start` and `stop`. There is no `pause` or `resume`; a service is only running or stopped. Connection context and payload identify the affected service. `application_shutdown` remains distinct because it stops the complete application session.

Command-result message types use `accepted`, `completed`, and `failed`. They reuse the originating command's message ID. `error` remains reserved for protocol or request errors rather than an accepted command that fails during execution.

An invalid initial-state message or protocol mismatch closes the TUI pipe and marks it degraded.

After readiness, an invalid message closes the connection and marks the TUI degraded. An unknown message type returns an error without closing the connection. IPC has no application-defined message-size limit while the endpoint remains an inherited local boundary.

The walking skeleton departs from this readiness/degrade contract for the moment: an unmatched or invalid message currently crashes the Hub rather than closing the connection gracefully. This is intentional — see the Working rule in `REFACTOR_TODO.md` for the fail-fast rationale.

## Message identity and ordering

Deferred in full for the walking skeleton: commands are one-off and fire-and-forget (`_handle_message` routes `type` straight to an action, no response, no `message_id` in use anywhere). Deferred target, kept for whenever a correlated response is actually needed: the request-ID representation remains unresolved; one synchronized Hub method would own request allocation in memory and preserve request identity across child restarts; new orchestrator messages would allocate a sequence, responses and errors would reuse it, receivers would tolerate duplicates and gaps, automatic retries would reuse the original message ID and sequence.

## Health and connection loss

The Hub monitors every child's process sentinel and pipe endpoint. For live, backfill, and pipeline, pipe EOF means the Hub itself is gone — the only signal of Hub loss they have. The TUI and dashboard do not poll their pipe for EOF at all; both are long-lived and non-cyclic. Command timeouts identify an unresponsive TUI that remains alive. A restarted child receives a new pipe under the standard worker-restart policy. Worker crash restart uses the standard retry policy and then waits for manual restart.

Hub shutdown stops every child with `SIGTERM`/`process.terminate()` — the same call for all five roles, though they act on it differently: live, backfill, and pipeline treat it as a flag checked between cycles; the TUI acts on it directly in its handler; the dashboard has no handler and simply terminates. Every child then gets a flat fifteen-second wait if still alive, then kills and joins a process that still remains alive. This is a confirmed, documented exception to the standard retry policy below (one flat wait, not four escalating ones) — not a drift from it. It removes the process from its registry only after confirmed exit.

## Command lifecycle

Deferred in full — the walking skeleton only sends one-off commands with no tracked lifecycle. Deferred target: an in-memory request ledger recording each command before dispatch; states `pending`, `accepted`, `completed`, `failed`, `unknown`; a one-second acceptance timeout and a command-specific completion timeout, both producing `unknown` when missed; "late acceptance restarts the completion timer"; a failed-command retry creating a new request ID; a manual retry of an `unknown` request reusing the same ID.

## Request ledger

Deferred in full, same basis as above — no ledger exists or is needed while commands are fire-and-forget. Deferred target: an in-memory ledger for the application session storing message ID, status, and creation/last-update timestamps in UTC Unix microseconds; one-hour expiry with retry still available after expiry; duplicate-ID short-circuiting, returning stored status instead of executing again; excluding command payloads, results, credentials, and secret values; discarded whole on Hub exit. UUID message IDs would keep accidental ID collision out of scope independent of any of this — duplicates would only ever arise from the deferred retry path.

## Process lock

The Hub first acquires `hub.lock` in the per-user runtime directory. Child processes require no locks because the Hub creates them and retains their process handles.

Linux and WSL use `fcntl.flock`. File existence never proves ownership.

The locked file stores JSON metadata containing the Hub PID and process start time as UTC Unix microseconds. After acquisition, the Hub truncates the same file, writes fixed lifetime metadata once, flushes, and synchronizes it before launching children. The file remains stable and is never atomically replaced. Readers retry malformed or incomplete metadata under the standard policy. Persistent unreadable metadata means startup failure and requires restart.

## Replacement and orphan cleanup

A new `spex` invocation that finds the Hub lock held forcibly terminates the existing main process before acquiring the lock. That termination reaches only the old Hub's specific PID, not its children — POSIX does not propagate a killed parent's signal to them. Closing the old Hub's pipe endpoints as it dies causes live, backfill, and pipeline to see EOF and follow their graceful shutdown path. The TUI and dashboard have no equivalent: they are orphaned unless the replacement (or whatever killed the old Hub) also reaches their process group, which a plain PID-targeted kill does not. Accepted for now — the realistic path to a PID-targeted kill is Ctrl-C (which reaches the whole process group, TUI and dashboard included) already having failed, at which point that failure is the bug to fix. The active Hub supervises current-session children through retained process handles and uses forced termination after graceful shutdown fails.

## Application shutdown

Closing the TUI sends an application-shutdown request to the orchestrator. The orchestrator stops every child — live, backfill, pipeline, the TUI, and dashboard — with `SIGTERM`, joins each, and releases session resources. Unexpected TUI exit triggers the same application-shutdown policy because Spex has no headless operating mode. Unexpected orchestrator failure is visible to live, backfill, and pipeline through pipe EOF. The TUI and dashboard have no automatic detection of it at all, the same gap described under Replacement and orphan cleanup.

## Standard retry policy

Every retrying operation uses four exponential intervals within a 15-second retry window. Retry indices `0` through `3` use `2 ** retry_index` seconds: 1, 2, 4, and 8 seconds. An exception requires a documented design decision.

## Open questions

- What command-specific completion timeouts does profiling support?
- What payload fields do the final command and error messages require?
- How does the orchestrator assign request identity to operator intents originating in the TUI?
- What concrete request-ID representation does the Hub use?
