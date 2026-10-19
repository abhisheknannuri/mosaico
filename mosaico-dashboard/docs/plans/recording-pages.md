# Plan: recording detail, stream inspector, charts, computed data

Status: proposal (2026-10-18). Agreed parts become backlog tasks; diagrams move to
`architecture.md` as they are implemented.

## 1. Navigation

```mermaid
flowchart LR
    SB["Sidebar: Recordings"] --> LIST["/recordings<br/>list"]
    LIST -- "click row" --> OV["/recordings/{name}<br/>Overview tab"]
    OV <-- "tab" --> ST["/recordings/{name}/streams<br/>Streams tab"]
    ST -- "click row" --> IN["/recordings/{name}/streams/{topic}<br/>Stream inspector"]
    IN -- "← back" --> ST
```

- Every view has its own URL (shareable, back button). Tabs are boosted links.
- The topic is the **last** path segment (`{topic:path}`, topics contain `/`). JSON endpoints
  take the topic as a query parameter (`?topic=/imu/data`).
- No recording list inside the sidebar (does not scale); "Recordings" stays highlighted.

## 2. Views

| View | For | Content |
|---|---|---|
| Overview tab | everyone | tiles (recorded, duration, size, streams, uploaded), coverage, sensors by category, metadata (readable, nested values collapsible), uploads |
| Streams tab | analysts, developers | per topic: path, sensor label + tag, ROS type, messages, rate, duration, size |
| Stream inspector | developers | header + SDK snippet, schema tree with types, **interactive charts** (distribution per field, time series), preview by sensor type, first N raw messages |

### Interactive charts (W&B-style, for a static dataset)

| Chart | Shows | Interaction |
|---|---|---|
| Distribution (per numeric field) | real histogram; lines for mean, min, max; shaded ±1σ band; optional fitted normal curve | hover → bin range, count, share; field picker |
| Time series (per field) | value over time, downsampled to screen width (mean line + min/max band) | crosshair with values at cursor; drag/scroll to zoom → re-fetch window in full detail |
| Coverage timeline | one bar per stream over the recording; gaps (phase 3) | hover → stream, start, end, gap ranges |
| Storage bars (overview) | already CSS; can move to ECharts later | hover → exact bytes |
| GPS track / point cloud | track on lat/lon plane; lidar top-down or 3D (`echarts-gl`) | zoom, hover |

Histogram, not a drawn bell curve: sensor data is often multi-modal or clipped; a curve drawn from
mean and std would misrepresent it.

## 3. Charting: Apache ECharts 6.1.0, the one library

- One library for every chart (distribution, time series, timeline, bars, scatter, 3D add-on);
  vendored like htmx (`static/vendor/echarts-6.1.0.min.js`, ~1 MB, ~330 KB gzipped, cached by
  the browser); `echarts-gl` only on point-cloud pages. Apache-2.0.
- Rejected: uPlot (only lines/bars → would need a second library), Plotly (~3.5 MB, slow DOM),
  Chart.js (weak on large data and ranges).
- **Server sends data, not chart code.** The backend returns plain JSON (bins, counts, stats,
  series); one JS module turns it into an ECharts option per chart type. Swapping the library
  later touches only that module.

```mermaid
flowchart LR
    subgraph SERVER["Server (Python)"]
        TPL["Jinja template<br/>&lt;div data-chart='distribution'<br/>data-src='/api/v1/...'&gt;"]
        API["web/api/*.py<br/>JSON: bins, counts, stats"]
    end
    subgraph BROWSER["Browser"]
        CJS["static/js/charts.js<br/>registry: distribution, timeseries,<br/>timeline, track"]
        EC["ECharts<br/>(Mosaico dark theme)"]
    end
    TPL -- "HTML (page or htmx fragment)" --> CJS
    CJS -- "fetch data-src" --> API
    CJS -- "option for chart type" --> EC
```

`charts.js` initialises every `[data-chart]` element on page load **and** after every htmx swap
(`htmx:afterSettle`), and disposes charts that htmx removes. Adding a chart type = one function
in the registry + one API endpoint.

## 4. System: processes and storage

```mermaid
flowchart TB
    BR["Browser<br/>HTML + htmx + ECharts"]

    subgraph DASH["mosaico-dashboard (same image, two processes)"]
        WEB["web process<br/>FastAPI: pages, fragments, JSON API"]
        WRK["worker process<br/>runs computation jobs"]
    end

    DDB[("dashboard-db (Postgres 18)<br/>stats, histograms, jobs, artefacts")]
    CACHE[["cache folder (volume)<br/>thumbnails, clips, renders"]]
    MD["mosaicod<br/>Arrow Flight"]

    BR <-- "HTTP" --> WEB
    WEB -- "live metadata,<br/>bounded reads" --> MD
    WEB -- "read results,<br/>enqueue jobs" --> DDB
    WEB -- "serve files /media/..." --> CACHE
    WRK -- "claim jobs,<br/>write results" --> DDB
    WRK -- "stream full topics" --> MD
    WRK -- "write files" --> CACHE
```

- Web never reads a whole topic; worker never serves HTTP.
- Compose: `dashboard-db` (own volume `dashboard-pg-data`, host port 5433) and `dashboard-cache`
  volume; in development the app and worker run from the venv, cache in `mosaico-dashboard/.cache/`.

## 5. Code decomposition (new files in **bold**)

```mermaid
flowchart TB
    subgraph WEB["web/"]
        P1["pages/recording.py<br/>overview + streams tabs"]
        P2["pages/stream.py<br/>inspector"]
        A1["api/stats.py<br/>distribution JSON"]
        A2["api/series.py<br/>time-series JSON"]
        MEDIA["/media mount<br/>(cache folder)"]
    end

    subgraph SVC["services/"]
        S1["recording.py<br/>detail, streams + rate"]
        S2["inspect.py<br/>schema, raw messages, series"]
        S3["stats.py<br/>cached or enqueue"]
    end

    subgraph DATA["data access"]
        GW["gateway/sdk.py<br/>+ stream_schema, read_messages,<br/>read_fields(window)"]
        DB["db/<br/>engine, tables, repositories"]
        FS["media/<br/>cache paths, file writes"]
    end

    subgraph JOBS["jobs/ (worker only)"]
        Q["queue.py<br/>enqueue, claim, finish"]
        H1["compute_stats.py"]
        H2["render_frames.py"]
        W["worker.py (entrypoint)"]
    end

    DOM["domain/<br/>+ StreamDetail, SchemaField,<br/>FieldStats, Histogram, Series<br/>+ aggregate.py (numpy: Welford,<br/>histogram, buckets)"]

    P1 --> S1
    P2 --> S2
    P2 --> S3
    A1 --> S3
    A2 --> S2
    S1 --> GW
    S2 --> GW
    S3 --> DB
    S3 --> Q
    W --> Q
    Q --> DB
    W --> H1
    W --> H2
    H1 --> GW
    H1 --> DB
    H2 --> GW
    H2 --> FS
    S1 --> DOM
    S2 --> DOM
    H1 --> DOM
    GW --> DOM
```

Import rules (extend `import-linter`): `web → services → (gateway | db | media) → domain`;
`jobs` may import `services`, `gateway`, `db`, `media`, `domain`, never `web`; only `gateway`
imports the SDK; `domain` stays pure (numpy allowed).

## 6. Flows

### 6.1 Overview / Streams tab (live, phase 1)

```mermaid
sequenceDiagram
    participant B as Browser
    participant P as pages/recording.py
    participant S as services/recording.py
    participant G as gateway (SdkGateway)
    participant M as mosaicod

    B->>P: GET /recordings/demo_warehouse_run_01/streams
    P->>S: get_streams(name)
    S->>G: list_streams(name)
    G->>M: sequence + topic metadata (incl. total_row_count)
    M-->>G: metadata
    G-->>S: SensorStream (+ message_count)
    S-->>P: StreamRow list (rate = messages / duration)
    P-->>B: page, or table fragment for htmx
```

### 6.2 Statistics: cache miss → job → result (phase 3)

```mermaid
sequenceDiagram
    participant B as Browser
    participant P as pages/stream.py
    participant S as services/stats.py
    participant D as dashboard-db
    participant W as worker
    participant M as mosaicod

    B->>P: GET .../streams/imu/data (inspector)
    P->>S: get_field_stats(name, topic)
    S->>D: SELECT stream_stats
    D-->>S: none
    S->>D: INSERT job compute_stats (if not queued)
    P-->>B: page with "Computing…" fragment (hx-trigger every 2s)
    W->>D: claim job (FOR UPDATE SKIP LOCKED)
    W->>M: stream topic chunk by chunk
    M-->>W: Arrow batches
    W->>W: running min/max/mean/std, then histogram pass
    W->>D: INSERT stream_stats + field_histogram, job done
    B->>P: poll stats fragment
    P->>S: get_field_stats
    S->>D: SELECT
    D-->>S: rows
    P-->>B: fragment with [data-chart=distribution]
    B->>B: charts.js fetches /api/v1/... and draws
```

Next visit: the first `SELECT` hits and the chart appears immediately. Results never expire
(immutable data); they are deleted with the recording.

### 6.3 Camera frames / video (phase 3–4)

```mermaid
sequenceDiagram
    participant B as Browser
    participant P as pages/stream.py
    participant D as dashboard-db
    participant W as worker
    participant C as cache folder
    participant M as mosaicod

    B->>P: inspector of a camera topic
    P->>D: artefact frames for (recording, topic)?
    D-->>P: missing → enqueue render_frames
    P-->>B: "Preparing preview…" (poll)
    W->>M: read K frames spread over the recording
    W->>C: write thumb_000.jpg … (Pillow), later clip.mp4 (PyAV)
    W->>D: INSERT artefact rows
    B->>P: poll
    P-->>B: frame strip + slider, src=/media/{recording}/{topic}/thumb_*.jpg
    B->>C: GET /media/... (static files)
```

### 6.4 Job lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued: enqueue (unique per kind + recording + topic)
    queued --> running: worker claims
    running --> done: results written
    running --> failed: error (message stored)
    failed --> queued: retry (max 3)
    done --> [*]
```

## 7. Dashboard database (phase 2–3)

```mermaid
erDiagram
    JOB {
        uuid id PK
        text kind "compute_stats | render_frames"
        text recording
        text topic
        text status "queued | running | done | failed"
        int attempts
        text error
        timestamptz created_at
        timestamptz finished_at
    }
    STREAM_STATS {
        text recording PK
        text topic PK
        text field PK "dotted path, e.g. acceleration.x"
        bigint count
        bigint null_count
        float min
        float max
        float mean
        float std
        timestamptz computed_at
    }
    FIELD_HISTOGRAM {
        text recording PK
        text topic PK
        text field PK
        float_array bin_edges
        bigint_array counts
    }
    ARTEFACT {
        text recording PK
        text topic PK
        text kind PK "frames | clip | bev"
        text path "relative to cache folder"
        timestamptz created_at
    }
    STREAM_STATS ||--|| FIELD_HISTOGRAM : "same field"
```

- Keys are (recording, topic[, field]); no foreign keys to mosaicod (separate system).
- When a recording disappears from mosaicod (catalog sync), its rows and cache folder are deleted.
- Cache folder layout: `{recording}/{topic-slug}/thumb_000.jpg`, `clip.mp4`, `bev.png`.

## 8. Phases and order

```mermaid
flowchart LR
    P1["Phase 1: detail pages, live<br/>overview tab, streams tab (messages, rate),<br/>inspector v1 (schema, raw messages), row links"]
    P2["Phase 2: infrastructure<br/>dashboard-db, Alembic, worker + job queue,<br/>cache folder, ECharts + charts.js"]
    P3["Phase 3: inspect, computed<br/>stats + distribution chart, time series,<br/>camera frame strip, GPS track, coverage gaps"]
    P4["Phase 4: rich previews, export<br/>video clips, lidar top-down/3D,<br/>CSV/Parquet/MCAP download, shared time cursor"]
    P1 --> P2 --> P3 --> P4
```

The catalog index (fast list and filters) and storage history reuse the phase-2 infrastructure.
