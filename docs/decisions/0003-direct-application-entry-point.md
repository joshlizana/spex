# Use a direct application entry point

Status: accepted

## Context and problem statement

Spex uses Textual as its operational interface and orchestrator and does not provide structured headless commands. The application needs a direct entry point without exposing orchestration through a CLI framework.

## Decision drivers

- `spex` launches one interactive application.
- The Textual interface owns operator controls and configuration.
- The Textual control plane owns process orchestration without an argument parser.
- Spex does not require structured headless commands, shell completion, or command-specific option validation.

## Considered options

- Use Typer for the application entry point and public subcommands.
- Hand-build a command-line parser and orchestration interface.
- Use a direct package entry point into the Textual control plane.

## Decision outcome

Chosen option: **Use a direct package entry point into the Textual control plane**, because Textual owns both operator interaction and orchestration and Spex exposes no structured headless command interface.

### Consequences

- The `spex` console script launches the application directly.
- The Textual application owns child processes, control connections, lifecycle state, and operator actions.
- Typer is not a runtime dependency.
- Spex defines no public ingestion, backfill, processing, dashboard, or status subcommands.
- A future command-line interface requires a new demonstrated product need and a separate decision.

### Confirmation

Compliance requires Typer to be absent from runtime dependencies and `spex` to launch the Textual control plane directly.
