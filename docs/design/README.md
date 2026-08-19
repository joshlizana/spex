# Design

This directory contains product and technical design documents, interface sketches, specifications, and design explorations.

Technical design documents use [`../templates/tdd.md`](../templates/tdd.md). They state their status (`proposed`, `accepted`, `superseded`, or `implemented`) and separate confirmed requirements from open questions.

## Current documents

- [`architecture.md`](architecture.md) defines system structure, layers, dependencies, and process boundaries.
- [`process-control.md`](process-control.md) defines orchestration, IPC, process identity, locking, supervision, and request tracking.
- [`pipeline-data-flow.md`](pipeline-data-flow.md) defines ingestion, raw retention, processing, recovery, and analytical storage.
- [`verification-strategy.md`](verification-strategy.md) defines functional, recovery, cross-platform, performance, and scale verification.
