# Jetstream v2 Protocol

Research date: 2026-08-23

## Goal

Identify the official Jetstream v2 interfaces, cursor semantics, historical replay flow, live-stream flow, filtering, and delivery guarantees relevant to Spex.

## Method

Review the official `bluesky-social/jetstream` design specification, Jetstream Lexicons, public Go client documentation, and the installed `atproto==0.0.71` Python distribution. Treat the Lexicons as authoritative for the wire contract and inspect `atproto_jetstream` for Python client behavior.

## Evidence

### Jetstream v2 uses sequence-number cursors

Jetstream assigns each event a monotonic 64-bit sequence number. The sequence number is the cursor. Sequence numbers start at `1`, while `0` represents the position before the first event. A live WebSocket cursor is inclusive and replays events with `seq >= cursor`.

### Historical ranges use `(afterSeq, beforeSeq]`

The `network.bsky.jetstream.planSnapshot` XRPC procedure accepts optional `afterSeq` and `beforeSeq` parameters. The range excludes `afterSeq` and includes `beforeSeq`. Calling `planSnapshot` with `afterSeq=0` requests the complete sealed archive.

### Snapshot planning is paginated

Each plan page returns ordered segment or block work, `sealedTipSeq`, and `plannedThroughSeq`. The client pins `sealedTipSeq` as the upper bound, downloads and processes the planned work, then requests another page with `afterSeq=plannedThroughSeq` and `beforeSeq=sealedTipSeq`. The archive sweep completes when `plannedThroughSeq >= sealedTipSeq`.

### The Python replay API cuts over to one live WebSocket

`atproto_jetstream.JetstreamClient.replay()` and its asynchronous counterpart process the sealed archive, then connect to `/xrpc/network.bsky.jetstream.subscribeEvents` with `cursor=max(sealedTipSeq, lastProcessedSeq)`. This connection covers the active segment and live tail. The API exposes the operation as one non-terminating iterator.

### Delivery is at least once

Cursor replay is inclusive, and the service guarantees at-least-once delivery. The Python client sets its in-memory cursor to the archive cutover sequence before opening the live connection, then drops any live event whose sequence is less than or equal to that cursor. The same comparison suppresses inclusive redelivery during reconnects. Spex still needs idempotent processing because a crash can leave a durable raw record ahead of its persisted cursor.

Sequence cursors are local to a Jetstream server instance. A sequence value from another server is not interchangeable, so data provenance needs to identify the serving instance.

### Record keys are scoped to collections

AT Protocol defines a repository record path as `<collection>/<rkey>`. The same `rkey` may appear in multiple collections within one DID repository, so `(DID, rkey)` is not unique. The protocol identifies `(DID, collection, rkey)` as the unique logical record path. Repository `rev` is a monotonically increasing logical clock for a repository commit and does not add collection identity.

Spex includes collection identity and uses `(DID, collection, rkey, rev)` as the natural key for commit-record mutations.

### Filters apply to history and live data

The v2 interfaces support event-kind, DID, and collection filters. Supported event kinds are `commit`, `identity`, `account`, and `sync`. Collection filters accept exact NSIDs and namespace wildcards ending in `.*`.

### Live replay has a bounded lookback

The v2 WebSocket rejects a sequence cursor below its lookback floor with the structured `CursorTooOld` error. A client then returns to archive replay from its last processed sequence.

### Archive replay contains current repository records, not complete mutation history

A Jetstream v2 server bootstraps by downloading every record present in known repositories, then archives subsequent live events. Existing records may originate from the beginning of the Bluesky data plane in 2022. The initial archive does not reconstruct every update or record deleted before the server observed it. Jetstream retains the latest record version rather than full version history.

The repository README labels Jetstream v2 as pre-production. The active US East v2 status and XRPC endpoints provide direct evidence of a hosted deployment.

### The US East v2 host exposes archive status

A read-only probe identifies `jetstream.us-east.bsky.network` as the US East v2 host. On 2026-08-18, its status page reports:

- Steady-state operation
- `41,294,581` downloaded repositories
- `24,768,433,612` archived events
- Full sequence range `[1, 24,848,577,663]`
- Witnessed range `2026-08-04 13:12:56` through `2026-08-18 07:56:13`
- Live WebSocket lookback of approximately 36 hours

The witnessed range reflects when this Jetstream instance observes or bootstraps records. Record content may originate earlier. A request to `network.bsky.jetstream.planSnapshot` without a valid bearer credential returns an authentication error.

## Conclusions

- Spex identifies historical ranges with Jetstream sequence numbers.
- A full archive replay starts with `afterSeq=0`.
- Spex needs durable sequence checkpoints and idempotent event processing.
- Sequence number is the protocol-supported deduplication candidate within one Jetstream server instance.
- Captured-data provenance needs to identify the Jetstream server because sequence cursors are instance-local.
- Logical record identity requires collection as well as DID and rkey.
- Spex identifies commit-record mutations with `(DID, collection, rkey, rev)`.
- The data mart retains commit events and excludes identity, account, and sync events.
- Spex requests commit events for `app.bsky.feed.post`, `app.bsky.feed.repost`, `app.bsky.feed.like`, `app.bsky.graph.block`, and `app.bsky.graph.follow`.
- Spex applies no DID filter.
- User-configured retention may exceed the history available from the selected Jetstream instance; the TUI warns that archive availability varies.
- One ingestion service uses `atproto_jetstream.replay()` for HTTP/XRPC archive replay and the subsequent WebSocket live tail.
- Ingestion exposes `replay` and `live` as its only phases.
- The SDK owns the handoff from history to live using the sealed archive tip and last processed sequence.
- Spex needs an explicit policy for default range bounds and filters.
- `afterSeq=0` means the start of a specific Jetstream server's archive, not every historical mutation on Bluesky.
- The US East host exposes a sequence range starting at `1`, with bootstrap witnessed timestamps beginning on 2026-08-04.
- HTTP/XRPC archive access requires a bearer credential.
- Spex uses only `jetstream.us-east.bsky.network`; its sequence checkpoints and deduplication scope do not cross Jetstream instances.
- Clean first-run ingestion with archive access begins replay at the configured retention boundary; without archive access it begins in the live phase at the current tip.
- Live resumption replaces a saved checkpoint older than the active retention window with the retention-boundary sequence.

## Next steps

- Determine how a requested timeframe maps to `afterSeq` and `beforeSeq`.
- Select the default historical range.
- Select the event kinds, DIDs, and collections retained by Spex.
- Design durable cursor storage and idempotent folding.
- Validate sequence uniqueness across captured live and archive samples before selecting the data-mart key.
- Profile the five selected record collections and define their analytical transformations.
- Map the configured retention boundary to the initial replay cursor.
- Confirm archive authentication requirements for `jetstream.us-east.bsky.network`.

## Sources

- [Jetstream v2 design specification](https://github.com/bluesky-social/jetstream/blob/main/docs/README.md)
- [Official Jetstream v2 Go client documentation](https://github.com/bluesky-social/jetstream/blob/main/doc.go)
- [`atproto` Python SDK](https://github.com/MarshalX/atproto)
- [Jetstream v2 client protocol notes](https://github.com/bluesky-social/jetstream/blob/main/specs/client.md)
- [Jetstream v2 repository status](https://github.com/bluesky-social/jetstream)
- [Jetstream US East status](https://jetstream.us-east.bsky.network/status)
- [AT Protocol record-key specification](https://atproto.com/specs/record-key)
- [AT Protocol repository specification](https://atproto.com/specs/repository)
- [Canonical AT Protocol Lexicons](https://github.com/bluesky-social/atproto/tree/main/lexicons/app/bsky)
