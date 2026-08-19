# Supervise named services with multiprocessing processes

Status: accepted

## Context and problem statement

Spex needs to supervise five named, long-lived local processes with role-specific state, IPC identities, readiness, health, locks, graceful shutdown, and forced termination. Task-pool abstractions do not directly represent those service lifecycles.

## Decision drivers

- Each service has one stable role and distinct lifecycle behavior.
- The orchestrator requires direct process handles and exit observation.
- Spex uses authenticated `multiprocessing.connection` control channels.
- The application supports Linux, macOS, Windows, and WSL.
- The design avoids an external broker, daemon, or process manager.

## Considered options

- Direct `multiprocessing.Process` supervision.
- `asyncio` subprocess supervision.
- `concurrent.futures.ProcessPoolExecutor`.
- Joblib with Loky.
- Pebble process pools.
- MPIRE worker pools.

## Decision outcome

Chosen option: **Direct `multiprocessing.Process` supervision**, because it represents every Spex service as a named process with a direct lifecycle and preserves the established IPC, identity, locking, and shutdown contracts.

### Consequences

- The Textual control plane runs blocking process and connection supervision through functions decorated with `@work(thread=True)`.
- That control thread owns process creation, handles, exit observation, stop requests, and forced termination.
- Textual's main thread remains the exclusive owner of UI state and widget updates.
- Thread workers return state changes through `post_message()` or `call_from_thread()`.
- Worker targets remain importable and receive serializable startup arguments.
- Spex selects an explicit multiprocessing start context for cross-platform consistency.
- Pool libraries remain outside the application-orchestration boundary.
- Bounded parallel work inside a service may use a pool library when profiling supports it.

### Confirmation

Compliance requires every service to retain a direct `multiprocessing.Process` handle and role identity. Lifecycle verification covers startup, observed exit, graceful stop, forced stop, UI responsiveness, thread-safe UI updates, and supported-platform behavior.
