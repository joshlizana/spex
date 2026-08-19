# Jetstream collection message schemas

Research date: 2026-08-18

## Goal

Identify the Jetstream v2 commit envelope and the canonical AT Protocol record schemas for the five collections Spex ingests.

## Method

Inspect the official Jetstream v2 event type and the canonical AT Protocol Lexicon definitions on their main branches. Separate transport metadata from collection-owned record data.

## Evidence

### Jetstream v2 commit envelope

Every selected collection arrives inside a Jetstream event with `kind` equal to `commit`.

| Path | Type | Presence | Meaning |
| --- | --- | --- | --- |
| `did` | string | Required | Repository DID that owns the record. |
| `cursor` | unsigned integer | Required | Monotonic Jetstream event sequence and resume cursor. |
| `time_us` | integer | Required | Event display timestamp in Unix microseconds. |
| `kind` | string | Required | `commit` for the events Spex retains. |
| `commit.operation` | string | Required | `create`, `update`, or `delete`. |
| `commit.collection` | string | Required | Record collection NSID. |
| `commit.rkey` | string | Required | Record key within the collection. |
| `commit.rev` | string | Required | Repository revision that produced the mutation. |
| `commit.cid` | CID string | Create/update | Content identifier for the record; absent on delete. |
| `commit.record` | object | Create/update | Decoded AT Protocol record; absent on delete. |
| `commit.record_cbor` | bytes represented as base64 in JSON | Create/update when supplied | Canonical DAG-CBOR record; absent on delete. |

`time_us` represents Jetstream's selected event timestamp. It does not represent the record's client-declared `createdAt` value.

### Shared record structures

All five Lexicons use a transaction ID (`tid`) as the record-key type. Jetstream carries that key in `commit.rkey`.

AT Protocol JSON records include a `$type` discriminator containing the collection NSID. The collection Lexicons define the record properties below; `$type` identifies the concrete record type on the wire.

A `com.atproto.repo.strongRef` contains both required fields:

| Field | Type |
| --- | --- |
| `uri` | AT URI string |
| `cid` | CID string |

### `app.bsky.feed.post`

Required record fields:

| Field | Type | Constraints |
| --- | --- | --- |
| `text` | string | At most 3,000 bytes and 300 graphemes; an embed permits an empty value. |
| `createdAt` | datetime string | Client-declared creation time. |

Optional record fields:

| Field | Type | Constraints or reference |
| --- | --- | --- |
| `entities` | array | Deprecated `#entity` objects. |
| `facets` | array | `app.bsky.richtext.facet` objects. |
| `reply` | object | Required `root` and `parent` strong references. |
| `embed` | union | Images, video, gallery, external content, record, or record-with-media embed. |
| `langs` | array of language strings | At most three values. |
| `labels` | union | `com.atproto.label.defs#selfLabels`. |
| `tags` | array of strings | At most eight values; each value is at most 640 bytes and 64 graphemes. |

The deprecated `entities` shape requires `index`, `type`, and `value`. Its `index` requires non-negative integer `start` and `end` offsets.

### `app.bsky.feed.repost`

| Field | Type | Presence |
| --- | --- | --- |
| `subject` | strong reference | Required |
| `createdAt` | datetime string | Required |
| `via` | strong reference | Optional |

### `app.bsky.feed.like`

| Field | Type | Presence |
| --- | --- | --- |
| `subject` | strong reference | Required |
| `createdAt` | datetime string | Required |
| `via` | strong reference | Optional |

### `app.bsky.graph.block`

| Field | Type | Presence |
| --- | --- | --- |
| `subject` | DID string | Required |
| `createdAt` | datetime string | Required |

### `app.bsky.graph.follow`

| Field | Type | Presence |
| --- | --- | --- |
| `subject` | DID string | Required |
| `createdAt` | datetime string | Required |
| `via` | strong reference | Optional |

The Bluesky AppView ignores duplicate follow records. Spex preserves received mutations under its own retention and deduplication rules.

## Conclusions

- Validate the Jetstream envelope independently from the collection record.
- Validate `commit.record` against the collection Lexicon for create and update operations.
- Validate delete operations from their envelope because deletes omit `cid`, `record`, and `record_cbor`.
- Preserve the complete raw event before flattening. Post embeds, facets, labels, and deprecated entities introduce nested and polymorphic data.
- Use `cursor` for Jetstream ordering and checkpointing. Keep `createdAt` as source-authored record data.
- Treat the canonical Lexicons as evolving upstream contracts and profile captured events before fixing DuckDB transformation schemas.

## Next steps

- Capture representative create, update, and delete events for every selected collection.
- Profile optional post structures and observed extension fields.
- Define the walking-skeleton post projection from captured data.
- Define explicit DuckDB JSON schemas and flattening queries during validation-and-transformation design.

## Sources

- [Jetstream v2 event types](https://github.com/bluesky-social/jetstream/blob/main/event.go)
- [AT Protocol strong reference Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/com/atproto/repo/strongRef.json)
- [Post Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/post.json)
- [Repost Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/repost.json)
- [Like Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/like.json)
- [Block Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/graph/block.json)
- [Follow Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/graph/follow.json)
