# Textual and multiprocessing spawn compatibility

> Superseded outcome: Spex now runs Textual in the main process and spawns the Hub before entering the app. This preserves terminal input while keeping operational process creation outside Textual's event loop. The research below records the earlier failure and alternatives.

Research date: 2026-08-19

## Goal

Explain the `ValueError: bad value(s) in fds_to_keep` raised when the Textual action starts a spawned process on the WSL development environment, and identify the design constraint for Spex process startup.

## Method

The review reproduces process startup through the running TUI, traces the Python 3.14 multiprocessing call stack, inspects the installed Textual stream-capture implementation, and compares behavior after initializing a public spawn-context multiprocessing resource before Textual starts. Primary Python and Textual sources define expected behavior.

## Evidence

### The invalid descriptor comes from captured standard error

The failing resource-tracker launch passes `[-1, 6]` as inherited descriptors. Textual redirects standard error to its `_PrintCapture` object while processing application messages. Its `fileno()` method returns `-1`.

Python's POSIX resource tracker includes `sys.stderr.fileno()` when launching. CPython rejects negative entries in `fds_to_keep`, producing the observed exception.

### The resource tracker starts lazily

POSIX `spawn` and `forkserver` use a resource-tracker process. In the failing path, its first launch occurs inside the active Textual action after standard error redirection.

Creating a public `multiprocessing.Queue` from the spawn context before starting Textual launches the tracker while standard error has a valid descriptor. The same Textual action then starts its process without the descriptor error. This diagnostic confirms initialization timing as the cause; it does not select a queue as the production workaround.

### Start-method selection belongs at application startup

Python documents that `set_start_method()` belongs in the protected application entry point and should run at most once. It also provides `get_context()` for explicit, scoped creation of processes and multiprocessing resources.

## Conclusions

The failure does not come from the worker target or its arguments. It results from lazy POSIX resource-tracker startup while Textual captures standard error with an invalid file descriptor.

Calling `set_start_method("spawn", force=True)` inside the action does not correct the stream interaction and changes global multiprocessing state after the application is running. Spex uses one explicit spawn context in a dedicated main-process orchestrator. The orchestrator creates multiprocessing resources and child processes outside Textual's redirected standard streams, and Textual runs as an IPC spoke.

Spawned Textual terminal behavior requires Linux and WSL verification.

## Next steps

- Create all Spex processes and multiprocessing resources from one explicit spawn context.
- Verify spawned Textual input, rendering, signals, exit, and terminal restoration on Linux and WSL.
- Recheck current Python and Textual releases before retaining a compatibility workaround.

## Sources

- [Python multiprocessing contexts and start methods](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods)
- [Textual application source](https://github.com/Textualize/textual/blob/main/src/textual/app.py)
- [CPython multiprocessing utility source](https://github.com/python/cpython/blob/main/Lib/multiprocessing/util.py)
- [CPython POSIX subprocess source](https://github.com/python/cpython/blob/main/Modules/_posixsubprocess.c)
