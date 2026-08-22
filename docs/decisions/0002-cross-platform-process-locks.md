# Use One Hub Advisory File Lock

Status: accepted

## Context and problem statement

Spex needs to prevent a second Hub from owning the application session on Linux and WSL.

## Decision drivers

- Linux and WSL support
- Automatic lock release when a process exits
- No stale PID-file recovery
- One application lock
- No additional runtime dependency

## Considered options

- `fcntl.flock` advisory locks
- PID-file existence checks

## Decision outcome

Chosen option: **`fcntl.flock` advisory locks**.

Spex uses `fcntl.flock` on Linux and WSL. The lock file persists on disk and file existence does not indicate lock ownership.

`platformdirs` resolves the per-user runtime directory that contains `hub.lock`.

Child processes require no locks because the Hub creates them, retains their process handles, and assigns each a dedicated pipe.

When a new `spex` invocation finds `hub.lock` actively held, it forcibly terminates the existing Hub before acquiring the lock. The lock file records process identity used to target the active owner. Closing the old Hub's pipe endpoints causes every child, including Textual, to follow its graceful pipe-loss shutdown path.

### Consequences

- Process exit releases the operating-system lock.
- A persistent unlocked file does not block startup.
- Duplicate-instance checks depend on successful lock acquisition rather than PID-file contents.
- Starting `spex` replaces an active orchestrator and its application session.
- Safe forced replacement validates the recorded PID and process start time against the active lock owner.
- Child uniqueness follows Hub ownership rather than per-child locks.
- Current-session child termination uses retained process handles.
- Runtime paths follow platform conventions.
- Linux and WSL tests confirm equivalent exclusivity and process-exit release semantics.

### Confirmation

Linux and WSL tests attempt concurrent acquisition, confirm that only one process obtains the lock, terminate the owner, and confirm that another process can acquire the persistent lock file.
