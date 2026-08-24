# Python process orchestration options

Research date: 2026-08-18

## Goal

Evaluate Python-native options for supervising Spex's long-lived local services without a command-line framework, external broker, container runtime, or system daemon.

## Method

Compare official documentation for the Python standard library, Joblib, Loky, Pebble, and MPIRE against the confirmed Spex process model:

- Four named child processes with different responsibilities: Textual, ingestion, processing, and Streamlit. This topology reflects the later consolidated-ingestion decision.
- A dedicated main-process orchestrator and a Textual child process.
- Explicit start, stop, restart, readiness, pipe-loss, and degraded states.
- Stable role ownership and service-instance identities.
- Linux and WSL behavior.
- Authenticated `multiprocessing.connection` control channels.
- Graceful service-specific shutdown followed by forced termination when required.

## Evidence

### Comparison

| Option | Primary abstraction | Named long-lived services | Explicit process handles | Fit for Spex |
| --- | --- | --- | --- | --- |
| `multiprocessing.Process` | One process running one target | Direct | Direct | Strong |
| `asyncio` subprocess APIs | Independently launched child programs | Direct | Direct async subprocess handles | Moderate |
| `ProcessPoolExecutor` | Futures submitted to a worker pool | Indirect | Pool-oriented | Weak |
| Joblib with Loky | Parallel function calls in a reusable pool | Indirect | Pool-oriented | Weak |
| Pebble | Timed tasks in thread or process pools | Indirect | Pool-oriented | Weak |
| MPIRE | Parallel map and worker-pool workloads | Indirect | Pool-oriented | Weak |

### `multiprocessing.Process`

The standard library exposes each child as a `Process` with lifecycle methods, an exit code, and a platform waitable `sentinel`. `multiprocessing.connection.wait()` can wait on process sentinels and pipe `Connection` objects together. Hub-created duplex pipes align with the lifetime-bound control-plane design.

This option leaves supervision policy in Spex. That policy already exists as product behavior: role identity, restart exhaustion, pipe loss, graceful drain, and forced termination. Direct process ownership keeps those rules visible instead of adapting them to pool semantics.

Linux and WSL operation requires explicit attention to importable targets, start methods, serializable startup arguments, and the protected application entry point. Python 3.14 uses a start method other than `fork` by default, so Spex cannot rely on inherited main-process state.

### `asyncio` subprocess APIs

`asyncio.create_subprocess_exec()` creates and manages independent child programs with async process handles. This fits an event-driven main process and gives direct control over return codes, termination, and standard streams.

Each Spex service would launch as a separate Python program or module entry point. Spex would still implement control IPC, role metadata, readiness, pipe-loss handling, and platform-specific process-tree behavior. This adds an executable boundary that the current one-package, `multiprocessing` design does not require.

### `concurrent.futures.ProcessPoolExecutor`

`ProcessPoolExecutor` schedules picklable callables into an interchangeable process pool and returns `Future` objects. Python 3.14 provides immediate pool-wide termination and kill operations. An abrupt worker exit breaks the executor and raises `BrokenProcessPool` for pool work.

Spex services are not interchangeable tasks. Each role owns distinct state, IPC identity, health, and graceful shutdown. Mapping these services onto pool workers obscures role ownership and still requires a separate supervisor around the executor.

### Joblib and Loky

Joblib's default Loky backend focuses on parallel function execution, reusable worker pools, serialization through cloudpickle, array memmapping, and control of nested native thread pools. Loky provides a reusable `ProcessPoolExecutor` designed to recover a worker pool and reduce repeated spawn cost.

These features suit independent analytical or CPU-bound batch tasks. They do not supply Spex's service protocol, stable role-to-process mapping, readiness exchange, pipe-loss behavior, or component-specific graceful drain. Joblib may be evaluated later inside a processing component if profiling identifies suitable independent work. It does not replace the application orchestrator.

### Pebble

Pebble extends process pools with per-task timeouts, remote tracebacks, worker replacement, and limits on tasks per worker. It improves failure handling for bounded submitted work.

Spex requires service lifetime control rather than per-call timeout control. Pebble retains the same pool-to-service impedance and does not remove the need for the existing control protocol.

### MPIRE

MPIRE provides convenient parallel map operations, worker-local state, initialization and exit hooks, timeouts, and worker lifespan controls. Its abstraction remains a worker pool processing collections of jobs.

MPIRE fits batch transformation experiments more closely than application supervision. Some performance features depend on `fork` and therefore do not apply uniformly to Windows.

## Conclusions

- Use direct `multiprocessing.Process` ownership for application orchestration.
- Build a small Spex-specific supervisor around named process specifications and direct process handles.
- Use one Hub-created duplex `multiprocessing.Pipe` per child for the control plane.
- Integrate process sentinels and control connections with the main event loop rather than polling every service independently.
- Keep pool libraries outside the orchestration boundary.
- Evaluate Joblib, Loky, Pebble, or MPIRE only for bounded parallel work inside a service after profiling demonstrates a need.
- Consider `asyncio` subprocesses only if independent executable service entry points become a requirement.

## Next steps

- Select the explicit multiprocessing start context used across supported platforms.
- Design the minimal supervisor interface for start, request-stop, observe-exit, and force-stop.
- Defer restart policy, pipe-loss handling, and control-path hardening to milestone 2.

## Sources

- [Python `multiprocessing` documentation](https://docs.python.org/3.14/library/multiprocessing.html)
- [Python `concurrent.futures` documentation](https://docs.python.org/3.14/library/concurrent.futures.html)
- [Python asyncio subprocess documentation](https://docs.python.org/3.14/library/asyncio-subprocess.html)
- [Joblib parallel processing documentation](https://joblib.readthedocs.io/en/stable/parallel.html)
- [Loky reusable executor documentation](https://loky.readthedocs.io/en/stable/)
- [Pebble documentation](https://pebble.readthedocs.io/en/stable/)
- [MPIRE documentation](https://slimmer-ai.github.io/mpire/)
