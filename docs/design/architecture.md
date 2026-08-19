# Spex System Architecture

Status: proposed

Spex uses progressive decomposition. This document defines system structure, ownership, dependencies, and process boundaries. Focused design documents define component behavior.

## Stakeholders

| Role | Stakeholder |
| --- | --- |
| Project owner and developer | Joshua Lizana |
| Primary user | Independent developer |
| Portfolio audience | Recruiters and potential employers |
| Documentation and review partner | Codex |

## Problem statement

Spex needs a controllable and observable pipeline that processes Bluesky Jetstream v2 data for operational monitoring, portfolio demonstration, personal retention, and analytical use. The system supports continuous live ingestion and historical backfills without coupling their lifecycles.

## Goals

- Process live and historical Jetstream data through explicit boundaries.
- Preserve valid analytical data and rejected source records in DuckLake.
- Control services and inspect health through a Textual control plane.
- Present read-only analytical views through Streamlit.
- Package every component as one cross-platform application.
- Use multiple processes for isolation and parallel execution.
- Demonstrate real-time and bulk-load data architecture.

## Non-goals

- Use Streamlit for operational control.
- Use Textual for record-level exploration.
- Require one process for every logical responsibility.
- Couple backfill availability to live-ingestion availability.
- Support alternate Jetstream hosts.
- Ship captured-event replay as an end-user feature.

## System context

```text
                          Spex application
┌──────────────────────────────────────────────────────────────────┐
│ Textual control plane                                           │
│        │ controls, supervises, and aggregates health            │
│        v                                                         │
│ Live ingestion ──┐                                              │
│                  ├──> Raw retention ──> Processing ──> DuckLake │
│ Backfill ────────┘                                      │       │
│                                                        v       │
│                                                    Streamlit    │
└──────────────────────────────────────────────────────────────────┘
       ^                    ^
       │ WebSocket          │ HTTP/XRPC archive
       └──────────── Bluesky Jetstream ────────────
```

Live ingestion and backfill operate independently and write through one logical raw-retention boundary. Validation and transformation consume completed raw batches. Streamlit reads DuckLake without controlling the pipeline.

## Process topology

| Process | Responsibilities |
| --- | --- |
| Textual control plane | Direct application entry point, operator interface, session ownership, supervision, configuration, and aggregate health |
| Live | Current Jetstream ingestion |
| Backfill | Historical Jetstream ingestion |
| Validation and transformation | Schema validation, normalization, and DuckLake loading |
| Streamlit | Read-only analytical dashboard |

The orchestrator is the main process. Its failure ends the application session and initiates child shutdown. A child failure degrades only the capability it owns. Starting either ingestion process ensures that validation and transformation runs. Processing drains and stops after the final ingestion process stops.

See [Process Control](process-control.md) for IPC, identity, supervision, locking, request-ledger, and shutdown behavior.

## Layer and dependency model

```text
Interface and control
├── Textual control plane ───────> Pipeline service contracts
└── Streamlit ───────────────────> DuckLake read access

Pipeline
├── Live ingestion
├── Historical backfill
└── Validation and transformation
          │
          v
Data
├── Ephemeral raw retention
├── DuckLake and rejected records
├── Checkpoints and service state
├── Request ledger
└── Configuration and credentials

Platform capabilities support every internal layer.
External Jetstream services feed the pipeline layer.
```

| Layer | Dependency rule |
| --- | --- |
| Interface and control | Textual owns operator interaction, service contracts, and control state. Streamlit uses read-only analytical data. |
| Pipeline | Uses external sources and data boundaries without owning user interfaces. |
| Data | Owns persistence semantics without owning orchestration. |
| Platform | Supplies process, IPC, locking, filesystem, path, logging, and health facilities without product workflow rules. |
| External systems | Remain outside Spex's trust and lifecycle boundary. |

Dependencies follow responsibility boundaries. Pipeline components exchange records through durable storage rather than direct service-to-service control. Logical layers do not create additional process boundaries.

See [Pipeline and Data Flow](pipeline-data-flow.md) for ingestion, raw retention, validation, transformation, DuckLake, retention, and recovery behavior.

## Product interfaces

The Textual application is the configuration, orchestration, and operational-health control plane. A direct console entry point launches it as the main process. Streamlit provides analytical exploration in its own process. Spex exposes no structured headless commands.

The `spex` command launches the main process and Streamlit. The TUI starts and stops pipeline workers. Closing the TUI shuts down the complete application.

## Deployment and dependencies

- `uv tool install spex` installs the complete application on Linux, Windows, and macOS.
- `jetstream.us-east.bsky.network` provides live WebSocket events and authenticated HTTP/XRPC archives.
- Textual provides the terminal interface.
- The package console script provides the direct application entry point.
- DuckLake provides the analytical data mart.
- Streamlit provides analytical dashboards.
- `platformdirs` resolves per-user application directories.

## Quality strategy

Functional, recovery, performance, scale, and cross-platform verification use captured Jetstream events where reproducibility or throughput matters. Live integration checks cover protocol compatibility. See [Verification Strategy](verification-strategy.md).

## Open structural questions

- Which logical responsibilities benefit from a different process boundary after profiling?
- Which analytical model and dashboard views define the initial release?
- Does ephemeral raw retention use JSON Lines or SQLite in WAL mode?
- What performance threshold justifies materializing current-state views?
