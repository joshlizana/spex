# Spex

Spex is a Bluesky Jetstream v2 data pipeline. It ingests live and historical event data, validates and transforms records, and serves analytics through a DuckLake data mart and Streamlit dashboard.

## Development status

Spex provides a basic Textual interface with a placeholder health indicator through the `spex` command. The orchestrator, pipeline services, operational health, DuckLake loading, and Streamlit views remain under development.

## Audience

Spex serves independent developers who want to operate and explore a personal social-media data pipeline. It also serves as a portfolio project for recruiters and potential employers evaluating data-architecture skills.

## Use cases

The primary use case demonstrates an architecture that handles real-time streams and bulk historical loads. The secondary use case retains a rich social-media dataset for personal exploration and supports analytical questions for personal or professional purposes.

## Interfaces

- A Textual terminal user interface sends operator commands, accepts and persists the Jetstream archive credential, and displays operational health.
- The main-process Hub owns orchestration, IPC, application state, and shutdown.
- A Streamlit dashboard presents analytical views backed by the data mart.

## Deployment

Spex packages all components as one application and runs them across multiple processes for parallel execution. It uses `uv` for deployment on Linux and WSL.

Install Spex:

```console
uv tool install spex
```

Run the application:

```console
spex
```

## Architecture

Spex uses focused logical components within one application, with one responsibility per component:

- Live-stream ingestion consumes Jetstream events over WebSocket.
- Historical backfill ingestion retrieves data from the same Jetstream endpoint over HTTP.
- Validation checks incoming records.
- Transformation prepares validated records for analytical use.
- A DuckLake data mart stores and serves transformed data.

The complete application runs six processes:

- Hub
- Historical backfill
- Live ingestion
- Validation and transformation
- Streamlit dashboard
- Textual terminal interface

Each process uses a lock file to prevent multiple instances.

Component boundaries support focused design and operation within the application.

See [`docs/design/architecture.md`](docs/design/architecture.md) for the system design.

## Documentation

- [`CHANGELOG.md`](CHANGELOG.md) records notable project changes.
- [`docs/TODO.md`](docs/TODO.md) tracks open project and documentation work.
- [`docs/design/`](docs/design/) contains design specifications and explorations.
- [`docs/decisions/`](docs/decisions/) records durable project decisions.
- [`docs/research/`](docs/research/) contains research notes and sources.
- [`docs/reviews/`](docs/reviews/) contains substantial code-review reports.
- [`docs/templates/`](docs/templates/) contains standard documentation templates.

The documentation records the system design, research, decisions, and review findings.
