# Notes from the first pass over D-16 to D-35

The first pass implemented D-16 to D-35 in one go, without review between tasks. It was undone
so we can redo the tasks one by one and decide each step together. The full code of that pass
is kept on the local branch `AN/backup-d16-d35` (never pushed); local ADRs 0018–0030 in
`docs/decisions/` describe its decisions in more detail. The recording overview tab (D-15 of
that pass) is parked separately on `AN/d15-recording-overview`. The task numbers below are the
old ones; `BACKLOG.md` (reordered 2026-10-19) refers to them as "first pass: D-xx".

For every task: what was built, what went wrong or was surprising, and the decisions that are
worth discussing again before redoing it. Numbers are from the live data (r2b + demo bags).

## Cross-cutting findings

- **Stale servers.** `poetry run` starts scripts as `python -c "...import_module(...)..."`, so
  `pkill -f mosaico-dashboard` misses them and an old server keeps serving old Python code.
  Stop by module path (`mosaico_dashboard.__main__`, `mosaico_dashboard.run_worker`) from a
  command whose own text doesn't contain the pattern (otherwise pkill kills its own shell).
- **SDK message counts** exist only on a data streamer (`streamer.msg_count`), not on
  `TopicHandler`. Opening and closing a streamer costs ~3–4 ms per stream.
  Upstream idea: expose `TopicHandler.message_count`.
- **SDK has no column selection.** Reading timestamps or a few fields transfers whole messages
  (including image bytes). Locally this was still fast (532 MB stream in 0.55 s).
- **SDK ontology descriptions** carry units ("Temperature value in Kelvin."), but the lookup
  `resolve_ontology_class` is in `mosaicolabs.models.core.helpers` (not public API).
  Units are inconsistent: Temperature in Kelvin, BatteryState temperature in °C.
- **Job kinds were versioned** (`compute_stats_v2`, `render_frames_v2`, …): bumping the version
  makes cached results recompute. Worked well; worth keeping.
- **Each task got a screenshot review**; most UI bugs were only visible that way (clipped
  markers, upscaled images, ECharts colour modes).

## Phase 1: recording pages, live

### D-16 · Streams tab (messages, rate)
- Built: `/recordings/{name}/streams` table (topic, sensor label + ontology tag · ROS type,
  messages, rate, duration, size), `tabs` macro, shared `pages/recording_base.html`,
  `SensorStream.message_count` + `rate_hz`, `number` / `rate` filters.
- Issue: counts need a streamer per stream, so `list_streams(..., message_counts=False)` by
  default; only the streams tab pays for counts.
- Decide again: is a per-stream streamer acceptable for recordings with hundreds of topics?

### D-17 · Coverage timeline (start/end)
- Built: overview card with one CSS bar per stream from first to last message, axis row aligned
  as a grid row; `CoverageRow` as fractions of the recording span.
- Finding: in `r2b_galileo_0` the stereo cameras start ~8 s after the chassis sensors.

### D-18 · Stream inspector v1
- Built: `/recordings/{name}/streams/{topic:path}` (topic without leading `/`, resolved back by
  trying `/topic` then `topic`), tiles, schema tree, "Load in Python" snippet with Copy, first
  20 messages loaded lazily (bounded read; bytes, long lists and enums made displayable).
- Issues: a flat schema list was unreadable (repeated `header` structs) → collapsible tree;
  Jinja `tojson` escapes `<>` → own `json` filter; `/tf_static` has a single message.

### D-19 · Notifications and error states
- Built: "Ingestion errors" card (lazy, from SDK sequence + topic notifications); gateway errors
  → 503 page (with the compose command) / 502 / 404; inline error fragment for htmx requests.
- Issue: htmx doesn't swap 4xx/5xx responses by default, so lazy cards stayed on "Loading…"
  forever → `<meta name="htmx-config">` with `responseHandling` that swaps errors.

## Phase 2: infrastructure

### D-20 · Dashboard database
- Built: compose `dashboard-db` (Postgres 18, port 5433, volume `dashboard-pg-data`), SQLAlchemy
  Core (sync) + psycopg 3, Alembic inside the package, migrate on start (continues with a
  warning if the DB is down), `/readyz` covers the DB, CI Postgres service.
- Tests: in-memory SQLite for fast tests, `database` marker for Postgres tests.
- Decide again: SQLAlchemy Core vs ORM; whether to tolerate a down DB at start.

### D-21 · Tables and repositories
- Built: `job` (unique kind + recording + topic), `field_stats` (statistics + histogram as JSON;
  the plan had two tables, merged into one because they are 1:1), `artefact`.
- Issues: SQLite returns naive datetimes → `utc()` helper; de-duplicated enqueue needed a
  savepoint to survive the unique-constraint race.

### D-22 · Job queue and worker
- Built: Postgres table as queue (`FOR UPDATE SKIP LOCKED`, 3 attempts, `reset_running` on
  start), worker process `mosaico-dashboard-worker` polling every 1 s, `factories.py` shared
  with the web app, compose worker + cache volume.
- Issues found live: the dev DB was not migrated when only the worker ran → worker migrates
  too, under a Postgres advisory lock; a down DB logged a warning every second → one warning
  per outage.

### D-23 · ECharts and charts.js
- Built: ECharts 6.1.0 vendored, `charts.js` registry (server sends JSON data, JS builds the
  chart option), ECharts loaded only when a page has a chart, Mosaico theme, draw on htmx
  swaps, dispose on cleanup, resize observer.

### D-24 · Cache folder and /media
- Built: `media/cache.py` (`{recording}/{topic-slug}/file`, refuses paths outside the cache),
  `/media` static mount.
- Open: nothing ever deletes cached files.

## Phase 3: inspect, computed

### D-25 · Aggregation (pure)
- Built: `RunningStats` (Chan/Welford chunked), histogram edges + chunked histogram,
  `bucket_series` (vectorised per time bucket). NumPy added.

### D-26 · Field statistics + distribution chart
- Built: gateway `read_columns` via SDK `DataFrameExtractor.to_pandas_chunks` (columns named
  `{topic}.{tag}.{path}`), two passes in the worker (running stats, then histograms), lazy card
  polling every 2 s, JSON API, `distribution` chart (bars, min/mean/max lines, ±σ band and
  normal fit as legend toggles).
- Checked: demo IMU `acceleration.z` mean 9.8102 / std 0.0492 vs generated 9.81 / 0.05.
- Issues: min marker clipped at the axis edge → half-bin padding; constant fields gave
  std 1.7e-18 → clamp to 0 (and version bump to recompute).

### D-26b · Units and field names
- Built: SDK ontology descriptions in the schema (units included), GPS `position.x/y/z` shown as
  latitude / longitude / altitude, description under each stats field.
- Issue: shared types describe leaves generically (Point3d "Vector x component") → leaves use
  their struct's description ("Lat/Lon/Alt (WGS 84)").
- Decision: no unit conversion; values stay as stored, the description says the unit.

### D-27 · Time-series chart
- Built: live windowed read, bucketed; mean line + min–max band, gaps break the line, crosshair,
  zoom re-fetches the visible window at full detail.
- Issues: more buckets than samples drew dots → at most one bucket per ~2 samples; GPS axis
  labels all "44.7" → `rangeFormatter` (decimals from the visible range), table values with 6
  significant digits; unknown field returned zeros → 404.

### D-28 · Camera frame strip
- Built: `gateway.read_frame(at_ns)` seeks and decodes until the first image; worker renders 24
  frames as JPEG (≤ 960 px) into the cache; viewer with slider and clickable strip.
- Finding: most r2b cameras are H.264 `CompressedImage`. Seeking works: the decoder rejects
  packets until the next keyframe (GOP 5), then frames are clean. Raw `Image` streams include
  16-bit depth → stretched to 8-bit grey (1st–99th percentile).
- Issues: 640 px frames were upscaled → 960 px; SDK logs a warning per rejected packet.

### D-29 · GPS track
- Built: track API (thinned to ≤ 2000 points, broken at gaps, haversine distance), ECharts
  lat/lon plane at equal metres per pixel (cos-latitude), start/end markers.
- Decision: no map tiles (no outside requests, works offline). Discuss: tile layer behind a
  setting?
- Finding: GPS noise inflates distance (270 m path vs 195 m straight line in the demo).

### D-30 · Coverage gaps
- Built: per-recording `scan_gaps` job reading every stream's timestamps; a gap = step > 5× the
  median step and > 1 s; new table `stream_gap` + migration; gaps drawn on the coverage rows.
- Found: demo run 02 GPS gap 15.1 s; r2b recordings have none.
- Deviation from the plan: no ECharts timeline, the CSS rows were enough. Discuss again.

## Phase 4: rich previews and export

### D-31 · Video clips
- Built: decode every frame, re-encode H.264 MP4 with PyAV (libx264 is bundled), ≤ 960 px,
  variable frame rate from recorded timestamps, first 2 minutes only.
- Numbers: 12 s 1920×1200 H.264 → 1.0 MB in 7.6 s; 532 MB colour stream → 0.3 MB in 16.6 s.
- Issues: depth flickered (per-frame stretch) → first frame's stretch for the whole clip;
  player black until played → `src="...#t=0.01"`.
- Discuss: remux H.264 without re-encoding instead (faster, full size, H.264 sources only).

### D-32 · Point-cloud preview
- Built: demo bag `demo_lidar_survey_01` (ray-cast room, 16 × 512 beams, 10 Hz) ingested with
  the SDK `LidarAdapter` override → ontology `Lidar` (x/y/z lists); live scan API; top view
  coloured by height with a scan slider.
- Issues: ECharts `large` scatter mode ignores per-point colours → off.
- Not handled: `PointCloud2` ingested without the override (raw bytes + field layout).
- Discuss: 3D (echarts-gl) or a side view.

### D-33 · CSV / Parquet download
- Built: `GET /api/v1/recordings/{name}/export?topic=&format=&start_ns=&end_ns=`; CSV streamed
  per chunk (binary fields left out, lists as JSON), Parquet with every field (spooled temp
  file).
- Issues: `ParquetWriter.schema` is already an Arrow schema; writer must close before its buffer.

### D-34 · MCAP download
- Built: SDK `ROSSequenceExtractor` rebuilds the recording as a rosbag2 MCAP, on request only
  (button → worker job → link), served from `/media`. Round trip checked: same topics, types
  and counts as the source bag; r2b_galileo_0 → 493 MB in 2.2 s.
- Issues: the extractor needs an explicit ROS distribution (not stored in metadata) → Humble;
  the job queue never re-runs a done job, so "prepare again" buttons were useless.
- Open: exports are full-size copies; disk clean-up needed.

### D-35 · Shared time cursor
- Built (code and tests, docs not finished): new recording tab "Explore" — pick a camera and a
  numeric signal; frames and the time series share the recording's time axis. Moving through
  frames draws a cursor line on the chart; hovering the chart shows the nearest frame.
- Issue: frames and plots were never on the same page (a stream is either a camera or numeric),
  so the cursor needed this new page; that page was my design, not in the plan.
- Not verified: the hover/cursor interaction in a real browser (screenshots can't show it).

## Plan doc changes made after D-15

`docs/plans/recording-pages.md` was edited during D-20/D-21 (ER diagram: statistics and
histogram merged into `field_stats`; note on job versions). This file is restored to its D-15
version; the later version is on the backup branch.
