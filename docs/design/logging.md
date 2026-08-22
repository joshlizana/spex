# Centralized application logging

Status: proposed

## Stakeholders

| Role | Stakeholder |
| --- | --- |
| Owner and developer | Joshua |

## Problem statement

Spex needs queryable logs from its orchestrator, Textual interface, and application services without concurrent file writers or terminal output that disrupts the TUI.

## Goals

- Collect Spex application logs through one orchestrator-owned writer.
- Store structured JSON Lines that DuckDB can query.
- Rotate logs by size and time.
- Expose a configurable log level and log readout through the TUI.
- Preserve session, service, process, and message context.

## Non-goals

- Use logging as service-control IPC.
- Collect Streamlit framework logs during the initial implementation.
- Store credentials, authentication keys, decrypted secrets, or complete raw event payloads in logs.
- Implement the logging system within the M0 walking skeleton.

## Design

The main-process orchestrator creates an unbounded `multiprocessing.Queue` from the application `spawn` context and passes it to every child, including the Textual process. Spex loggers submit records through `logging.handlers.QueueHandler`. A `QueueListener` thread in the orchestrator owns the handlers and remains the only application-log writer.

The logging queue carries telemetry only. Service commands, health, and lifecycle messages continue to use the established `multiprocessing.connection` control channel.

The listener writes one combined JSON Lines log beneath the Spex `platformdirs` log directory. Rotation occurs hourly. Spex retains ten rotated files and compresses them with Zstandard. Filenames remain unresolved.

The TUI controls one global Spex log level and provides a log readout screen. It reads persisted records from the combined JSON Lines log and never receives log records directly from service processes. The orchestrator owns rotation. The TUI only detects replacement of the active file and continues reading from the new file. File-following behavior, reader transition after rotation, refresh cadence, filtering, search, and pause behavior remain unresolved.

Each process binds its session ID, service role, and process-instance ID to its logger once during startup. Every record inherits that process context. Each record also includes a stable machine-readable event name, human-readable message, UTC timestamp, severity, logger name, process name, and process ID. Message ID, exception details, and numeric measurements appear when applicable. The remaining JSON schema details remain unresolved.

Spex dashboard-service logs join the combined application log. Streamlit framework output remains separate during the initial implementation.

Logging continues accepting records while child services and the TUI shut down. After every child exits, the orchestrator fully drains and stops the listener before closing durable handlers.

The multiprocessing module's internal logger does not submit `DEBUG` records through the same queue because Python documents a recursion and deadlock risk for that configuration.

## API

Logger configuration functions, process-context binding, TUI file-reading behavior, and the JSON record schema remain unresolved.

## Dependencies

- Python standard-library `logging`, `logging.handlers`, and `multiprocessing`.
- `platformdirs` for the per-user log directory.
- A Zstandard implementation remains to be selected.

## Testing

### Functional testing

The functional verification plan remains unresolved.

### Performance testing

The performance verification plan remains unresolved.

### Scale testing

The scale verification plan remains unresolved.

## Sources

- [Python logging handlers](https://docs.python.org/3/library/logging.handlers.html)
- [Python logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [Textual logging handler](https://textual.textualize.io/api/logging/)
