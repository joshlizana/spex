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

## Live ingestion

Live ingestion owns the WebSocket lifecycle, subscription filters, checkpoints, and ingestion health. On a clean first run it starts at the oldest available unsealed sequence within the configured retention window and continues through the live tail. It skips older events. A saved checkpoint older than the retention window advances to the retention-boundary sequence and produces a persistent warning until acknowledgment.

## Historical backfill

Backfill uses the authenticated Jetstream HTTP/XRPC archive. Sequence ranges follow `(afterSeq, beforeSeq]`, and sequence `0` identifies the archive start. Requested records remain within the configured data-mart retention window. Archive-bound discovery and timeframe-to-sequence mapping remain research tasks.

The TUI collects and persists the archive bearer credential in a master-password-protected encrypted file. It requests the master password only when a backfill needs the credential and keeps the unlocked credential available for that backfill session and its retries.

The walking skeleton reads the archive credential from an environment variable for backfill testing without persisting it. Persistent encrypted storage remains outside that slice.

## Ephemeral raw-retention boundary

Live and backfill write independently through one logical raw store. Concurrent sources can arrive out of order. Ingestion continues while processing is unavailable, subject to capacity.

Raw capacity defaults to 1 GiB and has a 400 MiB minimum. The minimum reserves one temporary and one completed 100 MiB file for each ingestion service. At capacity, ingestion pauses instead of intentionally dropping events. It resumes when usage falls at least 100 MiB below the limit.

JSON Lines and SQLite WAL remain benchmark candidates. Selection uses sustained-write, replay-read, crash-recovery, cleanup, concurrency, and settled and peak disk-use evidence.

## JSON Lines candidate

Live and backfill own separate temporary and completed files. Each service keeps its temporary file open until it reaches 100 MiB and publishes it through an atomic same-directory rename. Graceful shutdown publishes a non-empty partial file before processing finishes draining. Processing reads completed files only.

Sealed files use `.jsonl.zst`. In-memory DuckDB reads them with an explicit JSON schema, flattens nested records, and produces rows for DuckLake without an intermediate expanded file.

Each ingestion service keeps a durable state artifact in application data. It records the open temporary filename, last written filename, oldest checkpoint in the open file, owning service, and creation timestamp. Updates flush a same-directory replacement and atomically swap it into place. The artifact remains after raw consumption.

If state is missing or corrupt while files exist, recovery uses the first complete record in a non-empty open file or the final record in the newest completed file when the open file is empty. Safe reconstruction failure stops that service and reports degraded health. Absence of both state and files is a clean first run.

Crash recovery discards an incomplete trailing line, retains complete lines, rewinds to the file's oldest checkpoint, and resumes. Inclusive replay can produce duplicates. Ingestion advances its checkpoint after every complete line. Record durability precedes checkpoint durability. Profiling selects per-line or grouped filesystem synchronization.

## Validation and transformation

The combined processing service consumes completed raw batches. It orders events by Jetstream cursor within each insertion batch. Separate batches can reach DuckLake out of sequence.

Validation stops at the first schema error. Validation failures are non-retryable and write the full source payload and first error to rejected-record storage.

Transformation owns normalization, derived values, and analytical mappings. A transformation failure uses the standard retry policy. Exhaustion writes the full source payload and final error to rejected-record storage.

When the final ingestion worker stops, processing drains pending raw records within a profiling-selected timeout. At timeout it finishes and commits the current batch without a separate hard timeout, then starts no new batch. A failed commit uses standard retries. Exhaustion leaves the batch unconsumed and reports degraded health.

## DuckLake data mart

DuckLake preserves every distinct commit mutation inside a configurable rolling retention period that defaults to 24 hours. Retention age uses Jetstream `time_us`. `(DID, collection, rkey, rev)` is the mutation natural key.

Raw duplicates from replay or overlapping sources remain in ephemeral retention. Data-mart ingestion deduplicates them. A distinct older mutation arriving after a newer mutation remains part of history.

Current state selects the highest Jetstream cursor for each `(DID, collection, rkey)` within retained history. A latest delete removes the logical record from current state while preserving its mutation. Query-time resolution is the default; performance evidence can justify materialization.

Successful insertion into either mutation history or rejected-record storage confirms consumption. Inserted and duplicate raw copies then become eligible for deletion.

## Analytical retention

Startup and scheduled cleanup remove expired valid and rejected records. The schedule defaults to hourly and is configurable. Cleanup runs outside insertion. Failures use standard retries; exhaustion leaves a visible degraded state until a later cleanup succeeds. The TUI offers manual retry.

Retention has no configured maximum. A reduction warns about immediate data loss and requires confirmation. An increase offers a backfill for the newly included period and still applies when declined. The interface warns that Jetstream archive availability varies.

## Operational surface

The TUI exposes service state, throughput, lag, errors, available disk space, and retained rejection counts grouped by validation and transformation failure. It configures retention, cleanup interval, and absolute raw capacity. These settings persist through `platformdirs` configuration paths.

The TUI provides configuration and operational health only. Streamlit provides record-level analytical exploration through read-only DuckLake access.

The walking skeleton sends one live post and one backfilled post through the same raw-retention, transformation, DuckLake, and dashboard boundaries. Its dashboard displays a posts table and post counts grouped by repository DID. Spex retains the public Jetstream fields used by the slice without anonymization in local Spex storage.

## Open questions

- Which raw-retention candidate satisfies the benchmark acceptance criteria?
- What explicit DuckDB schemas and transformations follow from captured records?
- What rejected-record and analytical table schemas support the initial views?
- What drain timeout follows from representative profiling?
- What archive bounds does the hosted service expose?
