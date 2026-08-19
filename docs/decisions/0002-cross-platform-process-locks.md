# Use Platform-Native Advisory File Locks

Status: accepted

## Context and problem statement

Each Spex process needs to prevent a second instance of the same process from running across Linux, macOS, Windows, and WSL. Python exposes different standard-library file-locking primitives on Unix and Windows.

## Decision drivers

- Linux, macOS, Windows, and WSL support
- Automatic lock release when a process exits
- No stale PID-file recovery
- One consistent internal lock contract
- No additional runtime dependency

## Considered options

- Platform-native advisory locks behind one internal interface
- PID-file existence checks

## Decision outcome

Chosen option: **Platform-native advisory locks behind one internal interface**.

Spex uses `fcntl.flock` on Linux and macOS and `msvcrt.locking` on Windows. WSL uses `fcntl.flock` because Spex runs as a Linux process there. The lock file persists on disk and file existence does not indicate lock ownership.

`platformdirs` resolves the per-user runtime directory that contains the process lock files.

The stable filenames are `backfill.lock`, `live.lock`, `pipeline.lock`, `streamlit.lock`, and `tui.lock`.

When a new `spex` invocation finds `tui.lock` actively held, it forcibly terminates the existing TUI process before acquiring the lock. The lock file records process identity used to target the active owner. Child processes detect the resulting heartbeat loss and follow their graceful shutdown paths. The replacement TUI starts without waiting for old child processes to release their locks. Replacement service launches use the standard retry policy while an old child holds a process lock. Exhausted acquisition retries leave the replacement TUI operational, mark the affected service degraded, and expose a manual restart action. Spex does not continue automatic acquisition attempts after exhaustion. Degraded status identifies the affected service and current lock owner. Manual restarts use the standard retry policy and clear degraded status when successful.

### Consequences

- Process exit releases the operating-system lock.
- A persistent unlocked file does not block startup.
- Duplicate-instance checks depend on successful lock acquisition rather than PID-file contents.
- Starting `spex` replaces an active TUI without graceful TUI shutdown.
- Safe forced replacement requires validation that recorded process identity matches the active lock owner.
- Replacement startup may encounter old child-process locks during their heartbeat-loss shutdown window.
- A held child-process lock does not prevent the replacement TUI from operating.
- Lock acquisition tests cover the race between the final 15-second retry and the 15-second heartbeat-loss timeout.
- The internal interface normalizes platform-specific acquisition failures and release behavior.
- Runtime paths follow platform conventions.
- Cross-platform tests need to confirm equivalent exclusivity and process-exit release semantics.

### Confirmation

Platform-specific tests attempt concurrent acquisition, confirm that only one process obtains the lock, terminate the owner, and confirm that another process can acquire the persistent lock file.
