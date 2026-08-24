# Process Control

Status: proposed

This document defines application sessions, worker identity, IPC, supervision, locks, request tracking, and shutdown behavior.

## Ownership

The `spex` console entry point launches Textual in the main process. Textual creates a duplex pipe, spawns the Hub, and retains its process handle. The Hub owns the application session, operational-service lifecycles, pipes, configuration, credentials, logging, and aggregate health. Textual and every application service communicates only with the Hub.

Textual creates the Hub with `multiprocessing.Process` under an explicit `spawn` context. The Hub uses the same start method for each named operational-service child and retains their direct process handles. Pool executors remain outside application orchestration.

Textual creates its duplex Hub pipe and passes one endpoint during spawn. The Hub creates one pipe before spawning each operational child and retains the other endpoint under its known role and process handle. TUI connection reads cross Textual's thread-safe `post_message()` or `call_from_thread()` boundary and never mutate Textual objects from the connection thread. The Hub sends readiness, state, and health to Textual; Textual sends no service-lifecycle commands.

Ingestion and processing never receive an application command on their pipe. They send advisory state and health telemetry to the Hub and detect Hub loss through EOF from a daemon monitor thread; the orchestrator retains authoritative lifecycle state in its process registry and stops a worker directly with `process.terminate()`.

The TUI and dashboard have no bounded work cycle — the TUI blocks inside Textual's main-process event loop, and the dashboard has no cycle either. Each uses a daemon pipe-monitor thread. Textual's Linux driver clears `ISIG`, so Ctrl-C arrives as the input byte `\x03` and is ignored unless Spex binds it; no `SIGINT` reaches the TUI, Hub, or other foreground processes. The dashboard needs no signal handler because it is a read-only display with no in-flight state to protect. Its pipe carries Hub-loss detection and no application messages.

## Resource ownership

Components keep resources local until initialization succeeds. A component that acquires several resources uses an `ExitStack` to clean up partial initialization and transfers that stack to the long-lived owner after successful setup. Shutdown releases owned resources in reverse acquisition order.

Individual files and pipe connections use their context-manager interfaces directly. Components with one straightforward resource remain direct context managers and do not require an `ExitStack`.

## Walking-skeleton service state

M0 represents each worker (ingestion and processing) with one field: `running`. There is no paused state; a worker is either running or unavailable. Ingestion additionally reports one operational phase: `replay` or `live`.

The Hub starts ingestion, processing, and dashboard during application startup. Ingestion starts in `replay` when archive access is available and transitions to `live` through the SDK; live-only operation starts in `live`. Services run for the application lifetime. The Hub stops a worker with `process.terminate()` (`SIGTERM`) during application shutdown. A shared `ServiceProcess` handler catches the signal and ends the worker's current work cycle gracefully before exit.

## Process identity

The Hub identifies each service through the role, process handle, and pipe endpoint stored in its process registry. Session and instance identifiers remain outside the walking-skeleton control contract.

## IPC transport

Textual creates the dedicated TUI-Hub `multiprocessing.Pipe(duplex=True)`. The Hub creates a dedicated pipe for each operational child. Each owner and child close their unused endpoint copies after spawning. EOF identifies peer loss. A restarted process receives a new pipe.

The Hub retains each parent endpoint under the role and process handle it launched, so the pipe establishes transport identity without endpoint discovery or authentication. The Hub and the TUI exchange native Python dictionaries through `Connection.send()` and `Connection.recv()`. These methods use pickle and remain restricted to inherited pipes between Hub-created processes. Ingestion and processing send advisory telemetry but receive no application commands. Each worker monitors its connection from a daemon thread to detect Hub loss because the Hub sends nothing on that endpoint.

Every message contains a `type` and `payload`. Role identity remains connection context rather than a repeated message field. The initial state reports the protocol version once during readiness.

## Child readiness

The TUI's first message carries its initial state and protocol version. The Hub associates it with the dedicated pipe received from its Textual parent.

The TUI becomes ready after the Hub accepts its initial state. Pipe creation and transfer occur as part of process creation and have no connection retry or hello acknowledgment.

Acknowledgment message types use the `<type>_ack` naming convention. An acknowledgment confirms receipt or protocol acceptance and does not represent completion of an asynchronous operation.

The `state` message carries either one service update or a complete service snapshot, with its payload identifying the included scope. Ingestion state includes its `replay` or `live` phase. Worker telemetry is advisory; the Hub derives authoritative running/unavailable state from process handles and sentinels.

The TUI exposes no service-lifecycle messages. Closing Textual requests application shutdown through pipe EOF rather than an application message.

An invalid initial-state message or protocol mismatch closes the TUI pipe and marks it degraded.

After readiness, an invalid message closes the connection and marks the TUI degraded. An unknown message type returns an error without closing the connection. IPC has no application-defined message-size limit while the endpoint remains an inherited local boundary.

The walking skeleton still needs to implement this readiness and state contract. No command identity or request ordering is required because the TUI sends no lifecycle commands.

## Health and connection loss

Textual monitors the Hub's pipe from a daemon thread and retains the Hub process handle. The Hub monitors the TUI pipe plus every operational child's process sentinel and pipe endpoint. For ingestion and processing, pipe EOF means the Hub itself is gone. The TUI exits through Textual's thread-safe boundary on Hub EOF; the dashboard ends its placeholder loop on Hub EOF. Detecting a peer that remains alive but stops responding is deferred with the rest of the command lifecycle below; the walking skeleton has no command timeouts.

The Hub supervises from an `asyncio` loop in its own process, with no listener or handler threads. Each pass polls and receives the TUI endpoint, driving command handling, then judges every operational child by its process sentinel. TUI pipe EOF ends the loop because Spex has no headless mode. An operational child's exit is joined and dropped, and supervision continues. Advisory telemetry drainage remains deferred with its producers. Passes are separated by a fixed one-hundred-millisecond sleep.

Blocking calls stay off the event loop. `multiprocessing` joins are synchronous, so every terminate/kill escalation runs through `asyncio.to_thread`, and application shutdown escalates all children concurrently under a single `asyncio.gather` rather than serially. The Hub is an async context manager: teardown awaits the join before releasing the process lock, so the lock outlives every child it supervises. A restarted child receives a new pipe under the standard worker-restart policy. Worker crash restart uses the standard retry policy and then remains unavailable until the application restarts if attempts exhaust.

Hub shutdown stops every operational child with `SIGTERM`/`process.terminate()`. Ingestion and processing treat it as a flag checked between cycles, while the dashboard terminates directly. Every child then gets a flat fifteen-second wait if still alive, followed by kill and join if it remains alive. This is a confirmed exception to the standard retry policy below. The Hub removes a process from its registry only after confirmed exit.

## Process lock

The Hub child acquires `hub.lock` in the per-user runtime directory. Operational-service children require no locks because the Hub creates them and retains their process handles.

Linux and WSL use `fcntl.flock`. File existence never proves ownership.

The locked file stores JSON metadata containing the Hub PID and process start time as UTC Unix microseconds. After acquisition, the Hub truncates the same file, writes fixed lifetime metadata once, flushes, and synchronizes it before launching children. The file remains stable and is never atomically replaced. Readers retry malformed or incomplete metadata under the standard policy. Persistent unreadable metadata means startup failure and requires restart.

## Replacement and orphan cleanup

A new `spex` invocation whose Hub finds `hub.lock` held fails lock acquisition. Reporting that startup failure deterministically to the new Textual parent remains deferred with the Hub-ready handshake. If a Hub dies, its operational children observe pipe EOF and exit through their monitor threads; its Textual parent also observes EOF and exits through Textual's thread-safe boundary. Ctrl-C remains an ignored input byte while Textual disables `ISIG` unless Spex binds it.

## Application shutdown

Closing Textual closes its Hub endpoint and then joins the Hub process. Hub EOF stops ingestion, processing, and dashboard, joins them, releases the Hub lock, and exits. Unexpected Hub failure is visible to Textual and every operational child through pipe EOF from their monitor threads.

## Standard retry policy

Every retrying operation uses four exponential intervals within a 15-second retry window. Retry indices `0` through `3` use `2 ** retry_index` seconds: 1, 2, 4, and 8 seconds. An exception requires a documented design decision.

## Open questions

- What state and health payload fields does the TUI require?
