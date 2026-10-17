# ADR-0004: The dashboard has its own database and never touches mosaicod's

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** D-18 (implementation)

## Context

mosaicod's Postgres (`mosaicod/crates/mosaicod-db/migrations/`) is its **internal** catalog:
`sequence_t`, `session_t`, `topic_t`, `chunk_t` (which Parquet file in the object store holds
which data), `column_t` + `column_chunk_numeric_t` / `column_chunk_textual_t` (per-chunk min/max,
used to prune queries), `sequence_notification_t` / `topic_notification_t`, `api_key_t`,
`cleanup_log_t`, `topic_optimization_t`, `instance_registry_t`. Its schema changes often (three
migrations on 2026-10-14 alone).

The dashboard needs things mosaicod doesn't store or can't answer cheaply:
- a sortable/filterable **index** of recordings (the SDK needs one network call per sequence);
- **history** (daily storage snapshots for growth charts);
- **ingestion jobs** started from the browser;
- **summary statistics** per field (mean/std don't exist anywhere; per-chunk min/max exist only
  for query pruning and aren't exposed by the SDK).

## Decision

A separate Postgres **database** (`dashboard`), owned by the dashboard, with its own migrations.
In development it may live on the same Postgres **server** as mosaicod's database, but with a
different database name and user. The dashboard reads Mosaico data **only through the SDK**:
never reads or writes mosaicod's tables directly.

| Dashboard table | What it holds | Rebuildable from mosaicod? |
|---|---|---|
| `recording`, `sensor_stream`, `upload_session` | Copy of catalog metadata, for fast queries | Yes (resync) |
| `stream_field_stats` | min/max/mean/std/count per numeric field | Yes (recompute, slow) |
| `storage_snapshot_daily` | Size per recording/sensor type per day | **No**: back it up |
| `ingestion_job`, `ingestion_event` | Uploads started from the dashboard | **No** |

## Alternatives considered

- **Read mosaicod's Postgres directly:** fast, but couples us to an internal, fast-changing schema
  and bypasses the API-key layer.
- **SQLite:** fine for a single user, but no JSONB/GIN for metadata filters and no
  `SKIP LOCKED` job queue; Postgres is already in the stack.
- **No database (in-memory cache):** loses history and jobs on restart.

## Consequences

- Index can be stale by up to one sync interval; the UI shows "synced N s ago".
- Possible upstream proposal later: expose per-topic column stats via the SDK.
