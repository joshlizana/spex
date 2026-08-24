# Use a direct application entry point

Status: accepted

## Context and problem statement

Spex uses a dedicated orchestrator with Textual as its operational interface and does not provide structured headless commands. The application needs a direct entry point without exposing orchestration through a CLI framework.

## Decision drivers

- `spex` launches one interactive application.
- The Textual interface owns operator controls and configuration.
- The main-process orchestrator owns process orchestration without an argument parser.
- Spex does not require structured headless commands, shell completion, or command-specific option validation.

## Considered options

- Use Typer for the application entry point and public subcommands.
- Hand-build a command-line parser and orchestration interface.
- Use a direct package entry point into the application orchestrator.

## Decision outcome

Chosen option: **Use a direct package entry point into the application orchestrator**, because Spex exposes one interactive application without a structured headless command interface.

### Consequences

- The `spex` console script launches the application directly.
- The orchestrator owns child processes, control connections, and lifecycle state.
- Textual owns terminal interaction and sends operator actions through IPC.
- Typer is not a runtime dependency.
- Spex defines no public ingestion, replay, processing, dashboard, or status subcommands.
- A future command-line interface requires a new demonstrated product need and a separate decision.

### Confirmation

Compliance requires Typer to be absent from runtime dependencies and `spex` to launch the orchestrator directly.
