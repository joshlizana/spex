# Pipeline and Data Flow

Status: proposed

This document defines ingestion, ephemeral retention, processing, DuckLake loading, analytical retention, and pipeline recovery.

## Source scope

Spex connects only to `jetstream.us-east.bsky.network` and requests commit events for:

- `app.bsky.feed.post`
- `app.bsky.feed.repost`
- `app.bsky.feed.like`
- `app.bsky.graph.block`
- `app.bsky.graph.follow`

The pipeline accepts records from every available DID. It excludes identity, account, and sync events from the data mart. The canonical record shapes appear in [Jetstream collection message schemas](../research/jetstream-collection-schemas.md).

## Ingestion

One ingestion service owns archive access, the WebSocket lifecycle, subscription filters, the durable cursor, raw writes, and ingestion health. It uses the ATProto Python SDK's `atproto_jetstream` package rather than implementing archive planning, decoding, or cutover logic directly.

Ingestion exposes exactly two phases. During `replay`, `atproto_jetstream.replay()` consumes the sealed archive from an exclusive `after_seq` cursor. It then resumes the live subscription inclusively from the cutover sequence, suppresses sequence values at or below its in-memory cursor, and enters `live`. The SDK also suppresses inclusive redelivery during WebSocket reconnects.

On a clean first run with archive access, replay begins at the sequence corresponding to the configured retention boundary. Sequence `0` identifies the archive start. Without archive access, ingestion starts directly in `live` at the current tip. A saved cursor older than the retained archive range advances to the retention-boundary sequence and produces a persistent warning until acknowledgment.

The TUI collects and persists the archive bearer credential in a master-password-protected encrypted file. It requests the master password when replay needs the credential and keeps the unlocked credential available for the ingestion session and its retries.

The walking skeleton reads the archive credential from an environment variable for replay testing without persisting it. Persistent encrypted storage remains outside that slice.

## Ephemeral raw-retention boundary

Replay and live write serially through one logical raw store and one writer. Ingestion continues while processing is unavailable, subject to capacity.

M0 places raw files and DuckLake data under the Spex application-data directory resolved by `platformdirs`. Development resets may remove that application-specific directory after resolving and validating its exact path.

Raw capacity defaults to 1 GiB and has a 200 MiB minimum. The minimum reserves one temporary and one completed 100 MiB file for ingestion. At capacity, ingestion pauses instead of intentionally dropping events. It resumes when usage falls at least 100 MiB below the limit.

JSON Lines and SQLite WAL remain benchmark candidates. Selection uses sustained-write, replay-read, crash-recovery, cleanup, concurrency, and settled and peak disk-use evidence.

## JSON Lines candidate

Ingestion owns one sequence of temporary and completed files. It keeps its temporary file open until it reaches 100 MiB and publishes it through an atomic same-directory rename. Graceful shutdown publishes a non-empty partial file before processing finishes draining. Processing reads completed files only.

Sealed files use `.jsonl.zst`. In-memory DuckDB reads them with an explicit JSON schema, flattens nested records, and produces rows for DuckLake without an intermediate expanded file.

Ingestion keeps one durable state artifact beneath the Spex `user_state_path`. It records the open temporary filename, last written filename, oldest cursor in the open file, owning service, and creation timestamp. Updates flush a same-directory replacement and atomically swap it into place. The artifact remains after raw consumption.

If state is missing or corrupt while files exist, recovery uses the first complete record in a non-empty open file or the final record in the newest completed file when the open file is empty. Safe reconstruction failure stops ingestion and reports degraded health. Absence of both state and files is a clean first run.

Crash recovery discards an incomplete trailing line, retains complete lines, rewinds to the file's oldest checkpoint, and resumes. Inclusive replay can produce duplicates. Ingestion advances its checkpoint after every complete line. Record durability precedes checkpoint durability. Profiling selects per-line or grouped filesystem synchronization.

## Validation and transformation

The combined processing service consumes completed raw batches. It orders events by Jetstream cursor within each insertion batch. Separate batches can reach DuckLake out of sequence.

Validation stops at the first schema error. Validation failures are non-retryable and write the full source payload and first error to rejected-record storage.

Transformation owns normalization, derived values, and analytical mappings. A transformation failure uses the standard retry policy. Exhaustion writes the full source payload and final error to rejected-record storage.

When ingestion stops, processing drains pending raw records within a profiling-selected timeout. At timeout it finishes and commits the current batch without a separate hard timeout, then starts no new batch. A failed commit uses standard retries. Exhaustion leaves the batch unconsumed and reports degraded health.

## DuckLake data mart

DuckLake preserves every distinct commit mutation inside a configurable rolling retention period that defaults to 24 hours. Retention age uses Jetstream `time_us`. `(DID, collection, rkey, rev)` is the mutation natural key.

Raw duplicates from crash recovery can remain in ephemeral retention when durable raw writes advance ahead of the persisted cursor. Data-mart ingestion deduplicates them. A distinct older mutation arriving after a newer mutation remains part of history.

Current state selects the highest Jetstream cursor for each `(DID, collection, rkey)` within retained history. A latest delete removes the logical record from current state while preserving its mutation. Query-time resolution is the default; performance evidence can justify materialization.

Successful insertion into either mutation history or rejected-record storage confirms consumption. Inserted and duplicate raw copies then become eligible for deletion.

## Analytical retention

Startup and scheduled cleanup remove expired valid and rejected records. The schedule defaults to hourly and is configurable. Cleanup runs outside insertion. Failures use standard retries; exhaustion leaves a visible degraded state until a later cleanup succeeds. The TUI offers manual retry.

Retention has no configured maximum. A reduction warns about immediate data loss and requires confirmation. An increase offers replay for the newly included period and still applies when declined. The interface warns that Jetstream archive availability varies.

## Operational surface

The TUI exposes service state, throughput, lag, errors, available disk space, and retained rejection counts grouped by validation and transformation failure. It configures retention, cleanup interval, and absolute raw capacity. These settings persist through `platformdirs` configuration paths.

The TUI provides configuration and operational health only. Streamlit provides record-level analytical exploration through read-only DuckLake access.

The walking skeleton sends one replayed post and one live post through the same ingestion, raw-retention, transformation, DuckLake, and dashboard boundaries. Its dashboard displays a posts table and post counts grouped by repository DID. Spex retains the public Jetstream fields used by the slice without anonymization in local Spex storage.

## Open questions

- Which raw-retention candidate satisfies the benchmark acceptance criteria?
- What explicit DuckDB schemas and transformations follow from captured records?
- What rejected-record and analytical table schemas support the initial views?
- What drain timeout follows from representative profiling?
- What retention timeframe maps to the initial replay cursor?
