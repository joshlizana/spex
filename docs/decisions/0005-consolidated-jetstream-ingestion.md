# Consolidate Jetstream ingestion

Status: accepted

## Context and problem statement

Jetstream v2 exposes historical archive replay and the live tail as one ordered stream. The ATProto Python SDK's `atproto_jetstream` package plans and decodes the archive, transitions to the live WebSocket without a gap, and suppresses inclusive sequence overlap at the boundary. Separate live and backfill processes would divide one protocol lifecycle and require Spex to coordinate the cutover itself.

## Decision drivers

- Preserve Jetstream sequence order through the archive-to-live transition.
- Use the SDK's replay, decoding, cursor, reconnection, and seam-deduplication behavior.
- Keep one raw writer and one durable ingestion cursor.
- Avoid application-owned cutover coordination.
- Present a small operational state model.

## Considered options

- One ingestion service with `replay` and `live` phases.
- Separate live and backfill services coordinated by the Hub.
- A live service with one-off external backfill jobs.

## Decision outcome

Chosen option: **One ingestion service with `replay` and `live` phases**, because the process boundary follows the SDK's continuous replay-to-live lifecycle.

The `replay` phase consumes the sealed archive and includes all work before the cutover. The `live` phase begins when the SDK transitions to the WebSocket tail. Backfill is a behavior of replay, not a service or third phase.

### Consequences

- Spex runs Textual in the main process, a Hub child, and Hub-owned ingestion, processing, and Streamlit children.
- Ingestion owns one raw writer, one durable sequence cursor, and one service-state artifact.
- The Hub starts ingestion with the application, while the TUI reports its `replay` or `live` phase.
- Ingestion sends phase and health telemetry to the Hub while lifecycle commands remain signal-based.
- `atproto_jetstream.replay()` owns archive planning, decoding, and the gapless transition.
- The SDK drops sequence values at or below its in-memory cursor at the replay/live seam and during reconnects.
- Spex still processes records idempotently because a crash can leave durable raw data ahead of the persisted cursor.
- Archive credentials affect whether replay is available; they do not create a separate service lifecycle.

### Confirmation

Architecture review confirms one ingestion process and raw writer. Integration verification covers archive replay, the replay-to-live seam, reconnect redelivery, persisted-cursor restart, and downstream deduplication after crash recovery.
