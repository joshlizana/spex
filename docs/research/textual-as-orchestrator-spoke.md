# Textual as an orchestrator spoke

Research date: 2026-08-19

## Goal

Evaluate a process topology in which a dedicated main-process orchestrator owns service supervision and IPC while the Textual interface runs as a spawned client process. Determine the lifecycle, terminal, communication, and verification implications for Spex.

## Method

The research reviews the Python 3.14 multiprocessing process, connection, start-method, sentinel, and termination contracts alongside Textual's application and worker documentation. It applies those documented contracts to Spex's Hub-created child topology. Textual does not document spawned-child terminal ownership as a supported deployment pattern, so that behavior remains a Linux and WSL verification requirement.

## Evidence

### The orchestrator can retain direct supervision

Python exposes each child process's lifecycle, exit code, and waitable sentinel through its `Process` object. `multiprocessing.connection.wait()` accepts both connection objects and process sentinels. A main-process orchestrator can therefore observe commands, health messages, TUI disconnection, and child exits through one supervision boundary.

Only the process that creates a `Process` object should call its lifecycle methods. Making the orchestrator the sole parent of the TUI and all services preserves direct and unambiguous ownership.

### The TUI can use the existing control protocol

`multiprocessing.Pipe(duplex=True)` provides the Hub and TUI with paired message-oriented `Connection` endpoints. Connection closure produces EOF at the peer. Command timeouts cover a connected process that remains alive but unresponsive. The TUI uses the same request, response, and state dictionaries as the service children. The Hub associates the pipe with the `tui` role when it creates the process.

This boundary makes the orchestrator authoritative for process and service state. The TUI renders received snapshots and events and sends operator commands. It does not retain authoritative lifecycle state.

### Textual remains the exclusive terminal owner

Textual's normal `App.run()` mode reads from and writes to the terminal. The orchestrator can remain attached to the same console while abstaining from terminal input and output. Application logs must continue through the structured logging channel rather than standard output or standard error.

Python's `spawn` method starts a fresh interpreter and transfers only the resources required by the child. This avoids starting service processes after Textual has redirected standard streams. Python and Textual do not provide an explicit guarantee for a Textual application launched as a multiprocessing child, so interactive input, rendering, resize handling, signal handling, terminal restoration, and exit codes require verification on Linux and WSL.

### The TUI should remain non-daemonic

Python terminates daemonic multiprocessing children when their parent exits and does not join them. Forced termination skips exit handlers and `finally` clauses. Textual needs an orderly exit to restore terminal state, so the TUI should remain non-daemonic and participate in the normal shutdown protocol.

The orchestrator can request graceful TUI shutdown, wait for its process sentinel, and force termination only after the shutdown deadline. The TUI exits when its Hub connection closes. These rules provide parent dependency without daemon-process semantics.

### Cross-process UI updates stay inside the TUI

Textual documents most UI APIs as non-thread-safe and identifies `post_message()` as thread-safe. `call_from_thread()` schedules a callable on Textual's main thread. A connection-reader thread inside the TUI process can therefore receive hub messages and post custom Textual messages without transferring Textual objects across processes.

The connection-reader thread starts as part of the TUI after spawn transfers its pipe endpoint. The Hub creates every pipe before its child, so Textual worker startup does not gate service availability.

### Shutdown direction needs one authority

A normal TUI close can send one application-shutdown request to the orchestrator. The orchestrator then stops work, drains and terminates services, asks the TUI to exit, joins every child, and releases session resources. A TUI crash or disconnection should trigger the same application-level policy because Spex has no headless operating mode.

If the orchestrator fails, each spoke detects connection closure and exits gracefully. Forceful termination remains the final fallback because Python warns that terminating a process during connection or queue use can corrupt that channel and bypass cleanup.

## Conclusions

Textual as an orchestrator spoke fits Spex's hub-and-spoke control protocol and resolves the current resource-tracker timing conflict. The topology gives the orchestrator sole ownership of IPC, process handles, service state, retries, and shutdown while Textual owns only terminal interaction and presentation.

The recommended topology is:

1. The `spex` entry point bootstraps paths and configuration.
2. The main-process orchestrator creates the session, structured logging resources, and one duplex pipe per child.
3. The orchestrator spawns the non-daemonic TUI and service processes from one explicit `spawn` context.
4. Every child closes its unused endpoint copy and reports initial state through its assigned pipe.
5. The TUI sends commands and renders state exclusively through IPC.
6. TUI closure requests complete application shutdown.
7. Hub loss causes every spoke to exit through pipe-loss handling.

This topology adds one process and makes TUI responsiveness dependent on the IPC protocol. It also removes Textual objects and stream capture from the orchestration boundary. Spex adopts this topology subject to Linux and WSL terminal verification.

## Next steps

- Build a minimal lifecycle probe that launches Textual as a spawned non-daemonic child and verifies input, rendering, resize handling, graceful exit, hub-loss exit, terminal restoration, and return-code propagation on every supported environment.

## Sources

- [Python 3.14 multiprocessing documentation](https://docs.python.org/3.14/library/multiprocessing.html)
- [Python multiprocessing listeners and clients](https://docs.python.org/3.14/library/multiprocessing.html#listeners-and-clients)
- [Python multiprocessing connection waiting](https://docs.python.org/3.14/library/multiprocessing.html#multiprocessing.connection.wait)
- [Textual application API](https://textual.textualize.io/api/app/)
- [Textual workers and thread-safe UI messaging](https://textual.textualize.io/guide/workers/)
