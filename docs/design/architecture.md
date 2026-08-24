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

Spex needs a controllable and observable pipeline that processes Bluesky Jetstream v2 data for operational monitoring, portfolio demonstration, personal retention, and analytical use. One ingestion lifecycle replays available history and then continues with live events.

## Goals

- Process historical and live Jetstream data through one ordered ingestion boundary.
- Preserve valid analytical data and rejected source records in DuckLake.
- Control services and inspect health through a Textual interface connected to the orchestrator.
- Present read-only analytical views through Streamlit.
- Package every component as one Linux application that also runs under WSL.
- Use multiple processes for isolation and parallel execution.
- Demonstrate real-time and bulk-load data architecture.

## Non-goals

- Use Streamlit for operational control.
- Use Textual for record-level exploration.
- Require one process for every logical responsibility.
- Reimplement the Jetstream archive-to-live cutover outside the ATProto SDK.
- Support alternate Jetstream hosts.
- Ship captured-event replay as an end-user feature.

## System context

```text
                          Spex application
┌──────────────────────────────────────────────────────────────────┐
│ Hub ────────────────────> Textual operational interface          │
│        │ supervises and aggregates health                        │
│        v                                                         │
│ Ingestion ────────────> Raw retention ──> Processing ──> DuckLake│
│                                                         v        │
│                                                    Streamlit     │
└──────────────────────────────────────────────────────────────────┘
       ^                    ^
       │ HTTP/XRPC replay and WebSocket live tail
       └──────────── Bluesky Jetstream
```

The ingestion service has two phases: `replay` consumes the authenticated archive, and `live` follows the WebSocket stream after the SDK-managed cutover. Both phases write through one raw-retention boundary and one durable cursor. Validation and transformation consume completed raw batches. Streamlit reads DuckLake without controlling the pipeline.

## Process topology

| Process | Responsibilities |
| --- | --- |
| Textual | Main application entry point, terminal ownership, Hub process supervision, operator input, configuration views, and operational-health presentation |
| Hub | Orchestration, session ownership, IPC, operational-service supervision, configuration, ephemeral request state, logging, and aggregate health |
| Ingestion | Jetstream archive replay, seamless transition, live subscription, cursor ownership, and raw writes |
| Validation and transformation | Schema validation, normalization, and DuckLake loading |
| Streamlit | Read-only analytical dashboard |

Textual runs in the main process and owns the Hub process handle. The Hub owns the remaining service children. Loss of either Textual or the Hub ends the application session through their pipe. An operational child failure degrades only the capability it owns. Starting ingestion ensures that validation and transformation runs. Processing drains and stops after ingestion stops.

See [Process Control](process-control.md) for IPC, identity, supervision, locking, request tracking, and shutdown behavior.

## Layer and dependency model

```text
Interface and control
├── Textual ─────────────────────> Hub control contract
├── Hub ─────────────────────────> Pipeline service contracts
└── Streamlit ───────────────────> DuckLake read access

Pipeline
├── Ingestion
│   ├── Replay phase
│   └── Live phase
└── Validation and transformation
          │
          v
Data
├── Ephemeral raw retention
├── DuckLake and rejected records
├── Checkpoints and service state
├── Ephemeral request state
└── Configuration and credentials

Platform capabilities support every internal layer.
External Jetstream services feed the pipeline layer.
```

| Layer | Dependency rule |
| --- | --- |
| Interface and control | Textual owns operator interaction. The orchestrator owns service contracts and authoritative control state. Streamlit uses read-only analytical data. |
| Pipeline | Uses external sources and data boundaries without owning user interfaces. |
| Data | Owns persistence semantics without owning orchestration. |
| Platform | Supplies process, IPC, locking, filesystem, path, logging, and health facilities without product workflow rules. |
| External systems | Remain outside Spex's trust and lifecycle boundary. |

Dependencies follow responsibility boundaries. Pipeline components exchange records through durable storage rather than direct service-to-service control. Logical layers do not create additional process boundaries.

See [Pipeline and Data Flow](pipeline-data-flow.md) for ingestion, raw retention, validation, transformation, DuckLake, retention, and recovery behavior.

## Product interfaces

The Hub is the application orchestrator and control plane. Textual runs in the main process as its terminal-facing control and operational-health interface. Streamlit provides analytical exploration in its own process. Spex exposes no structured headless commands.

The `spex` command launches Textual, which creates a control pipe and spawns the Hub. The Hub creates control pipes and spawns the operational services. TUI actions request service transitions through IPC. Closing the TUI closes the Hub pipe, causing complete application shutdown.

## Deployment and dependencies

- `uv tool install spex` installs the complete application on Linux and WSL.
- `jetstream.us-east.bsky.network` provides live WebSocket events and authenticated HTTP/XRPC archives.
- The ATProto Python SDK's `atproto_jetstream` package owns archive planning, decoding, cursor-based reconnects, and the replay-to-live cutover.
- Textual provides the terminal interface.
- The package console script provides the direct application entry point.
- DuckLake provides the analytical data mart.
- Streamlit provides analytical dashboards.
- `platformdirs` resolves per-user application directories.

## Quality strategy

Functional, recovery, performance, scale, Linux, and WSL verification use captured Jetstream events where reproducibility or throughput matters. Live integration checks cover protocol compatibility. See [Verification Strategy](verification-strategy.md).

## Open structural questions

- Which logical responsibilities benefit from a different process boundary after profiling?
- Which analytical model and dashboard views define the initial release?
- Does ephemeral raw retention use JSON Lines or SQLite in WAL mode?
- What performance threshold justifies materializing current-state views?
