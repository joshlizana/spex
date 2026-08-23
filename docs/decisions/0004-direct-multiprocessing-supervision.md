# Supervise named services with multiprocessing processes

Status: accepted

## Context and problem statement

Spex needs to supervise five named child processes with role-specific state, IPC identities, readiness, health, graceful shutdown, and forced termination. These children are Textual, live ingestion, backfill, processing, and Streamlit. Task-pool abstractions do not directly represent those lifecycles.

## Decision drivers

- Each service has one stable role and distinct lifecycle behavior.
- The orchestrator requires direct process handles and exit observation.
- Spex uses one Hub-created duplex `multiprocessing.Pipe` control channel per child.
- The application supports Linux and WSL.
- The design avoids an external broker, daemon, or process manager.

## Considered options

- Direct `multiprocessing.Process` supervision.
- `asyncio` subprocess supervision (`asyncio.create_subprocess_exec`), rejected as the process-creation mechanism. This does not exclude an `asyncio` event loop as the Hub's supervision mechanism over `multiprocessing`-created children, which is what the Hub uses.
- `concurrent.futures.ProcessPoolExecutor`.
- Joblib with Loky.
- Pebble process pools.
- MPIRE worker pools.

## Decision outcome

Chosen option: **Direct `multiprocessing.Process` supervision**, because it represents every Spex service as a named process with a direct lifecycle and preserves the established IPC, identity, locking, and shutdown contracts.

The Hub creates every child and supplies its duplex pipe endpoint during `spawn`. Children never discover or reconnect to an independently running Hub. This lifetime binding removes listener, endpoint-authentication, and connection-admission requirements while preserving message-oriented `Connection` semantics.

### Consequences

- The main-process orchestrator creates every child with `multiprocessing.Process` and retains its process handle.
- The orchestrator owns child monitoring independently of Textual's event loop, through pipe endpoints and process sentinels it holds directly.
- Textual's main thread remains the exclusive owner of UI state and widget updates.
- Textual connection handling returns state changes through `post_message()` or `call_from_thread()`.
- Worker targets remain importable and receive serializable startup arguments.
- Spex uses the `spawn` multiprocessing context on Linux and WSL.
- Pool libraries remain outside the application-orchestration boundary.
- Bounded parallel work inside a service may use a pool library when profiling supports it.

### Confirmation

Compliance requires the orchestrator to retain a direct `multiprocessing.Process` handle and role identity for every child under the `spawn` context. Lifecycle verification covers startup, observed exit, graceful stop, forced stop, UI responsiveness, thread-safe UI updates, and supported-platform behavior.
