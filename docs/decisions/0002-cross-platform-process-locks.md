# Use Advisory File Locks

Status: accepted

## Context and problem statement

Each Spex process needs to prevent a second instance of the same process from running on Linux and WSL.

## Decision drivers

- Linux and WSL support
- Automatic lock release when a process exits
- No stale PID-file recovery
- One lock contract
- No additional runtime dependency

## Considered options

- `fcntl.flock` advisory locks
- PID-file existence checks

## Decision outcome

Chosen option: **`fcntl.flock` advisory locks**.

Spex uses `fcntl.flock` on Linux and WSL. The lock file persists on disk and file existence does not indicate lock ownership.

`platformdirs` resolves the per-user runtime directory that contains the process lock files.

The stable filenames are `hub.lock`, `tui.lock`, `backfill.lock`, `live.lock`, `pipeline.lock`, and `streamlit.lock`.

When a new `spex` invocation finds `hub.lock` actively held, it forcibly terminates the existing Hub before acquiring the lock. The lock file records process identity used to target the active owner. Every child, including Textual, detects the resulting heartbeat loss and follows its graceful shutdown path. The replacement Hub starts without waiting for old children to release their locks. Replacement child launches use the standard retry policy while an old child holds a process lock. Exhausted acquisition retries leave the replacement TUI operational, mark the affected role degraded, and expose a manual restart action. Spex does not continue automatic acquisition attempts after exhaustion. Degraded status identifies the affected role and current lock owner. Manual restarts use the standard retry policy and clear degraded status when successful.

### Consequences

- Process exit releases the operating-system lock.
- A persistent unlocked file does not block startup.
- Duplicate-instance checks depend on successful lock acquisition rather than PID-file contents.
- Starting `spex` replaces an active orchestrator and its application session.
- Safe forced replacement requires validation that recorded process identity matches the active lock owner.
- Replacement startup may encounter old child-process locks during their heartbeat-loss shutdown window.
- A held child-process lock does not prevent the replacement orchestrator and TUI from operating.
- Lock acquisition tests cover the race between the final 15-second retry and the 15-second heartbeat-loss timeout.
- Runtime paths follow platform conventions.
- Linux and WSL tests confirm equivalent exclusivity and process-exit release semantics.

### Confirmation

Linux and WSL tests attempt concurrent acquisition, confirm that only one process obtains the lock, terminate the owner, and confirm that another process can acquire the persistent lock file.
