# Process Control

Status: proposed

This document defines application sessions, worker identity, IPC, supervision, locks, request tracking, and shutdown behavior.

## Ownership

The `spex` console entry point launches a dedicated main-process orchestrator. It owns the application session, child lifecycles, control pipes, control messages, configuration, credentials, request state, logging, and aggregate health. Textual and every application service communicates only with this Hub for control.

The orchestrator creates Textual and every named service child with `multiprocessing.Process` under one explicit `spawn` context and retains each direct process handle. All application process spawning uses multiprocessing. Pool executors remain outside application orchestration.

The orchestrator creates one duplex control pipe before spawning each child and passes one endpoint to that child. It retains the other endpoint under the child's known role and process handle. Inside the TUI process, connection reads cross Textual's thread-safe `post_message()` or `call_from_thread()` boundary and never mutate Textual objects from a connection thread. Textual actions send operator intents to the orchestrator through their pipe.

## Resource ownership

Components keep resources local until initialization succeeds. A component that acquires several resources uses an `ExitStack` to clean up partial initialization and transfers that stack to the long-lived owner after successful setup. Shutdown releases owned resources in reverse acquisition order.

Individual files and pipe connections use their context-manager interfaces directly. Components with one straightforward resource remain direct context managers and do not require an `ExitStack`.

## Walking-skeleton service state

M0 represents each service with two boolean fields: `running` and `paused`. When `running` is `false`, the service is inactive and the value of `paused` has no operational effect. When `running` is `true`, `paused=false` means active processing and `paused=true` means processing is paused.

A newly spawned worker starts with `running=true` and `paused=false`. The Hub spawns a worker in response to an operator start action, so startup begins work directly.

## Process identity

The Hub identifies each service through the role, process handle, and pipe endpoint stored in its process registry. Session and instance identifiers remain outside the walking-skeleton control contract.

## IPC transport

The orchestrator creates a dedicated `multiprocessing.Pipe(duplex=True)` for each child from the application `spawn` context. The orchestrator and child close their unused endpoint copies after spawning. EOF identifies peer loss. A restarted child receives a new pipe.

The Hub retains each parent endpoint under the role and process handle it launched, so the pipe establishes transport identity without endpoint discovery or authentication. Processes exchange native Python dictionaries through `Connection.send()` and `Connection.recv()`. These methods use pickle and remain restricted to inherited pipes between Hub-created processes.

Every message contains a `type` and `payload`. A message includes a `message_id` when it belongs to a request-response exchange. Role identity remains connection context rather than a repeated message field. The initial state reports the protocol version once during readiness.

## Child readiness

A child's first message carries its initial state and protocol version. The orchestrator associates it with the role and process handle recorded when launching the child.

The child becomes ready after the Hub accepts its initial state. Pipe creation and transfer occur as part of process creation and have no connection retry or hello acknowledgment.

Acknowledgment message types use the `<type>_ack` naming convention. An acknowledgment confirms receipt or protocol acceptance and does not represent completion of an asynchronous operation.

State exchange uses two message types. `state_request` asks the Hub for current state. `state` carries either one service update or a complete service snapshot, with its payload identifying the included scope.

Service-control message types use the concise names `start`, `stop`, `pause`, and `resume`. Connection context and payload identify the affected service. `application_shutdown` remains distinct because it stops the complete application session.

Command-result message types use `accepted`, `completed`, and `failed`. They reuse the originating command's message ID. `error` remains reserved for protocol or request errors rather than an accepted command that fails during execution.

An invalid initial-state message or protocol mismatch closes the pipe and marks the service degraded. One pipe exists per service instance.

After readiness, an invalid message closes the connection and marks the service degraded. An unknown message type returns an error without closing the connection. IPC has no application-defined message-size limit while the endpoint remains an inherited local boundary.

## Message identity and ordering

The request-ID representation remains unresolved. One synchronized Hub method owns request allocation in memory and preserves request identity across child restarts.

New orchestrator messages allocate a sequence. Responses and errors reuse their request sequence. Services do not allocate outbound sequences. Receivers tolerate duplicates and gaps. Automatic retries reuse the original message ID and sequence. Timestamps remain informational and do not determine ordering.

## Health and connection loss

The Hub monitors child process sentinels and pipe endpoints. Pipe EOF triggers graceful child shutdown or marks the child unavailable at the Hub. Command timeouts identify an unresponsive child that remains alive. A restarted child receives a new pipe under the standard worker-restart policy. Worker crash restart uses the standard retry policy and then waits for manual restart.

Hub shutdown closes the service pipe before joining so pipe EOF starts the child's graceful exit. The Hub joins with the standard retry intervals, sends termination when the process remains alive, waits five seconds, then kills and joins a process that still remains alive. It removes the process from its registry only after confirmed exit.

## Command lifecycle

The orchestrator records each command in an in-memory request ledger before dispatch. Dispatch retries preserve the request identity. Exhausted dispatch transitions the request to `failed`.

Request states are `pending`, `accepted`, `completed`, `failed`, and `unknown`. `completed` and `failed` are terminal. Completion confirms the requested operational state. A failed-command retry creates a new request ID. A manual retry of an `unknown` request uses the same ID and requires no confirmation.

The orchestrator waits one second for acceptance. Missing acceptance or a command-specific completion timeout produces `unknown` without automatic command retry. Late acceptance restarts the completion timer. Late completion or failure resolves the request and removes its manual retry action.

## Request ledger

The Hub owns an in-memory request ledger for the application session. It stores message ID, status, creation time, and last-update time. Times use UTC Unix microseconds. It excludes command payloads, results, credentials, and secret values. Duplicate IDs return stored status without executing again.

The ledger expires records older than one hour. A retry remains available after its ledger entry expires. Hub exit discards the complete ledger because a new Hub begins a new application session.

## Process lock

The Hub first acquires `hub.lock` in the per-user runtime directory. Child processes require no locks because the Hub creates them and retains their process handles.

Linux and WSL use `fcntl.flock`. File existence never proves ownership.

The locked file stores JSON metadata containing the Hub PID and process start time as UTC Unix microseconds. After acquisition, the Hub truncates the same file, writes fixed lifetime metadata once, flushes, and synchronizes it before launching children. The file remains stable and is never atomically replaced. Readers retry malformed or incomplete metadata under the standard policy. Persistent unreadable metadata means startup failure and requires restart.

## Replacement and orphan cleanup

A new `spex` invocation that finds the Hub lock held forcibly terminates the existing main process before acquiring the lock. Closing the old Hub's pipe endpoints causes its children to follow their graceful pipe-loss shutdown paths. The active Hub supervises current-session children through retained process handles and uses forced termination after graceful shutdown fails.

## Application shutdown

Closing the TUI sends an application-shutdown request to the orchestrator. The orchestrator stops Streamlit and all pipeline workers through their component-specific graceful shutdown paths, asks Textual to exit, joins every child, and releases session resources. Unexpected TUI exit triggers the same application-shutdown policy because Spex has no headless operating mode. Unexpected orchestrator failure triggers spoke shutdown through pipe loss.

## Standard retry policy

Every retrying operation uses four exponential intervals within a 15-second retry window. Retry indices `0` through `3` use `2 ** retry_index` seconds: 1, 2, 4, and 8 seconds. An exception requires a documented design decision.

## Open questions

- What command-specific completion timeouts does profiling support?
- What payload fields do the final command and error messages require?
- How does the orchestrator assign request identity to operator intents originating in the TUI?
- What concrete request-ID representation does the Hub use?
