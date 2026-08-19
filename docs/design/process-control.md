# Process Control

Status: proposed

This document defines application sessions, worker identity, IPC, supervision, locks, request tracking, and shutdown behavior.

## Ownership

The Textual application is the orchestrator and user-facing control plane. The `spex` console entry point launches it directly. It owns the application session, child lifecycles, control messages, configuration, credentials, request state, and aggregate health. Child services connect only to the Textual control plane for control communication.

The Textual control plane creates every named child with `multiprocessing.Process` and retains its direct process handle. Pool executors remain outside application orchestration. The explicit cross-platform multiprocessing start context remains open.

Functions decorated with Textual's `@work(thread=True)` own blocking process and connection supervision so the event loop remains responsive. The Textual main thread exclusively owns widgets and reactive UI state. Thread workers return state changes through the thread-safe `post_message()` or `call_from_thread()` boundary and never mutate Textual objects directly. Textual actions remain in-process control-plane operations; only child communication crosses the IPC boundary.

## Session and service identity

The orchestrator generates a lowercase UUIDv4 session ID at startup and holds it for its lifetime. A replacement orchestrator creates a new session ID. The main process reuses the session ID as its instance ID.

Each worker generates a lowercase UUIDv4 service-instance ID for its process lifetime. A restart creates a new service-instance ID while retaining the current orchestrator session ID. Messages and logs carry the session and service-instance IDs.

## IPC transport

Processes use `multiprocessing.connection.Client` and `Listener`. Linux, macOS, and WSL use `AF_UNIX`; Windows uses `AF_PIPE`. Endpoints accept the same operating-system user only.

The orchestrator generates a random authentication key for each application session, keeps it in memory, and passes it directly to children during process creation. Messages use UTF-8 JSON bytes and never use pickle serialization. Every message contains a fixed protocol version, type, session ID, service-instance ID, UTC Unix timestamp in microseconds, and message ID. Message schemas reject unknown fields. A schema change requires a protocol-version change.

## Connection handshake

A worker writes and synchronizes its lock metadata before connecting. Its first message is `hello`, containing the protocol version, role, session ID, and service-instance ID. The orchestrator allows five seconds for this message, reads the actively locked role file, and validates the message against lock metadata and the active protocol.

A successful handshake returns `hello_ack` with the same identity fields. The worker becomes ready only after receiving it. The worker allows five seconds for the acknowledgment. A timeout invokes IPC reconnection under the standard retry policy with the same service-instance ID.

Malformed handshake JSON, identity mismatch, or protocol mismatch closes the connection and marks the service degraded. One connection exists per service instance. A duplicate connection leaves the established connection active and rejects the new connection. The orchestrator caches immutable lock metadata for the connection lifetime and does not reread it for every message.

After the handshake, malformed JSON closes the connection and marks the service degraded. An unknown message type returns an error without closing the connection. IPC has no application-defined message-size limit while the endpoint remains a same-user local boundary.

## Message identity and ordering

One synchronized orchestrator method owns a session-wide counter. It starts at `0`, remains in memory, and survives reconnections. JSON encodes the sequence as a decimal string. `{session_id}:{sequence}` forms the message ID and request ID.

New orchestrator messages allocate a sequence. Responses and errors reuse their request sequence. Services do not allocate outbound sequences. Receivers tolerate duplicates and gaps. Automatic retries reuse the original message ID and sequence. Timestamps remain informational and do not determine ordering.

## Health and connection loss

The orchestrator sends a heartbeat every five seconds. Three missed acknowledgments indicate connection failure. Workers detect main-process failure after 15 seconds without a heartbeat and enter graceful shutdown. Operational health reports connection loss separately from process failure.

IPC reconnection uses the standard retry policy. Exhaustion marks the service degraded and waits for a manual restart. Worker crash restart also uses the standard retry policy and then waits for manual restart.

## Command lifecycle

The orchestrator begins command dispatch and a durable `pending` ledger write concurrently. Dispatch retries preserve the request identity. Exhausted dispatch transitions the request to `failed`. A failed ledger insertion starts a replacement write containing the latest known state. Exhausted ledger writes degrade ledger health without blocking commands.

Request states are `pending`, `accepted`, `completed`, `failed`, and `unknown`. `completed` and `failed` are terminal. Completion confirms the requested operational state. A failed-command retry creates a new request ID. A manual retry of an `unknown` request uses the same ID and requires no confirmation.

The orchestrator waits one second for acceptance. Missing acceptance or a command-specific completion timeout produces `unknown` without automatic command retry. Late acceptance restarts the completion timer. Late completion or failure resolves the request and removes its manual retry action.

## Request ledger

The orchestrator is the only writer to a per-session SQLite ledger in the per-user application-data directory. Filenames use `requests-{timestamp}-{session_id}.sqlite3`, where the timestamp is compact UTC microsecond form `YYYYMMDDTHHMMSSffffffZ`.

The ledger uses WAL mode, `synchronous=NORMAL`, a five-second busy timeout, and SQLite automatic checkpointing. It stores message ID, status, creation time, and last-update time. Times use UTC Unix microseconds. It excludes command payloads, results, credentials, and secret values. Duplicate IDs return stored status without executing again.

The schema has an internal version. A mismatch recreates the ledger. Runtime corruption degrades ledger health, disposes the database sidecar set under the standard retry policy, and creates a fresh timestamped ledger with the same session ID. A successful later write clears degraded health.

Clean shutdown deletes the session database, WAL, and shared-memory files. Startup removes valid prior-session ledger sets without an integrity check. Cleanup accepts only regular files directly inside the ledger directory whose names contain a valid timestamp and UUIDv4. It leaves malformed names, unrelated entries, and symbolic links untouched. Symbolic links produce warnings. Individual failures use standard retries, log absolute paths after exhaustion, and do not prevent a fresh ledger.

Recurring cleanup removes records older than one hour in one transaction. A retry remains available after its ledger row expires.

Unix-like systems use directory mode `0700` and file mode `0600`. Windows uses inherited permissions from the per-user application-data directory.

## Process locks

Every process first acquires a platform-native advisory lock in the per-user runtime directory. Stable filenames are `backfill.lock`, `live.lock`, `pipeline.lock`, `streamlit.lock`, and `tui.lock`. The TUI file identifies the `orchestrator` role.

Linux, macOS, and WSL use `fcntl.flock`. Windows uses `msvcrt.locking`. One internal interface normalizes both. File existence never proves ownership.

The locked file stores JSON metadata containing owner PID, session ID, role, service-instance ID, and process start time. After acquisition, the process truncates the same file, writes fixed lifetime metadata once, flushes, and synchronizes it before readiness. The file remains stable and is never atomically replaced. Readers retry malformed or incomplete metadata under the standard policy. Persistent unreadable metadata means startup failure and requires restart.

## Replacement and orphan cleanup

A new `spex` invocation that finds the TUI lock held forcibly terminates the existing main process before acquiring the lock. The replacement rejects old-session connections and inspects child locks.

An actively held child lock supplies the PID for signaling. The replacement allows the 15-second heartbeat-loss window for graceful shutdown and then uses `SIGKILL` on Unix-like systems or `TerminateProcess` on Windows. Failure marks the role degraded while the TUI continues. Cleanup logs role, PID, session ID, and outcome.

The replacement TUI starts without waiting for old child locks. Service launches retry lock acquisition under the standard policy, then expose degraded health and manual restart. Current-session children use held process handles for termination. Unreadable old-session metadata prevents safe process identification and requires manual operating-system intervention.

## Application shutdown

Closing the TUI always stops Streamlit and all pipeline workers. Workers use their component-specific graceful shutdown paths. Unexpected orchestrator failure triggers the same child behavior through heartbeat loss.

## Standard retry policy

Every retrying operation makes four retries after the initial failure. Retry indices `0` through `3` wait `2 ** retry_index` seconds: 1, 2, 4, and 8 seconds. An exception requires a documented design decision.

## Open questions

- What are the concrete AF_UNIX and AF_PIPE endpoint addresses and permission checks?
- What command-specific completion timeouts does profiling support?
- What are the final command and error message schemas?
