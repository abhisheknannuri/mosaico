# Mosaico Dashboard Role: Prototype and Outreach Plan

## Recommendation

Do not try to build the whole dashboard before contacting Mosaico. First send a focused note expressing interest and asking for a short conversation about the role, current dashboard status, and integration boundaries. In parallel, prepare a small, clearly labeled, read-only prototype against a local `mosaicod` instance. Use it to demonstrate judgment and execution, not to imply the work is official or production-ready.

The strongest first slice is a **catalog explorer**: browse sequences, search by name, inspect metadata, topics, sessions, total bytes, and ingestion error notifications. Add a small operational overview using those same facts. This is useful to the stated audience, demonstrates backend and frontend skills, and can be built through the existing Python SDK without inventing a new daemon REST API.

## Repository Evidence and Constraints

- `mosaicod` exposes Apache Arrow Flight over gRPC; the daemon documentation describes SDKs as the supported abstraction. Do not have the browser speak Flight directly or assume REST endpoints exist.
- The Python SDK already provides `MosaicoClient.list_sequences()`, sequence/topic handlers, sequence metadata, session metadata, total storage bytes, and sequence notifications. These support a credible first catalog and basic health/activity views.
- Sequence metadata includes creation time, user metadata, sessions, and aggregate size. Session metadata includes start/completion timestamps, lock state, and topics. Notifications currently represent errors. These are not necessarily a live ingestion-progress API: do not show fabricated percentages or claim real-time job state.
- API keys grant global, coarse-grained permissions. A read-only dashboard key still has platform-wide read access. Keep all Mosaico credentials on the server, use a dedicated least-privilege key, and establish dashboard-user authorization before exposing it to multiple users.
- The existing development Compose setup provides PostgreSQL and an object-store service; the existing daemon Dockerfile uses a multi-stage build. Reuse project conventions where suitable, but do not assume dashboard deployment should modify daemon containers.

## Initial Product Slice

### Build first

1. **Catalog page**: paginated sequence list, name search, size, created time, and selected user metadata. Make loading, empty, error, and stale-data states visible.
2. **Sequence detail page**: sequence metadata, topics, sessions, size, and available time range where SDK exposes it.
3. **Ingestion/activity view**: recent sessions and error notifications; label status from actual session fields only. Explain in the UI when the daemon does not expose a progress signal.
4. **Storage summary**: current aggregate bytes and largest sequences. Label these as current-state metrics, not historical growth.
5. **Operational baseline**: health/readiness endpoint, structured logs, configuration through environment variables, and a repeatable local container run.

### Defer until confirmed with the team

- Browser upload and data transfer. Large multimodal files need resumability, limits, cancellation, cleanup, and a decision about whether the dashboard stages files or sends them through another supported path.
- Historical storage-growth charts. Current totals are not a history; trend reporting requires persisted periodic snapshots or a daemon-provided history source.
- Destructive actions, multi-user roles, and production authentication. Existing Mosaico API-key scopes alone do not provide per-user or per-sequence isolation.
- High-frequency payload visualization and broad BI query builder. Keep the first experience focused on catalog metadata and operational decisions.

## Proposed Technical Shape

- **Backend**: FastAPI, Pydantic response models, and a small service layer wrapping the existing Python SDK. Keep daemon access and credential handling out of route handlers. Use an async-compatible execution strategy for blocking SDK/Flight work; verify concurrency behavior instead of assuming SDK calls are async-safe.
- **Frontend**: server-rendered Jinja2 pages with semantic HTML and htmx for search, pagination, and targeted partial refreshes. Add only small client-side code for interactions that genuinely need it, such as charts. No SPA framework for the initial slice.
- **Data model**: initially treat `mosaicod` as source of truth and fetch catalog data through the SDK. Add a dashboard database only when a concrete need appears, such as historical metric snapshots, user accounts, or durable transfer jobs. Never duplicate raw sensor payloads in the BI store.
- **Transport boundary**: browser → dashboard HTTP → FastAPI service → Python SDK → Arrow Flight/gRPC → `mosaicod`. Keep the wire-protocol complexity behind the SDK.
- **Deployment**: an independent dashboard image/service, non-root runtime, health checks, explicit secret injection, TLS at the deployment boundary, and documented local Compose setup. Avoid baking API keys into images or browser assets.

## Two-Week Prototype Schedule

### Days 1–2: Verify and narrow

- Contact Mosaico before investing in broad implementation; ask whether dashboard work already exists and what interfaces/deployment target they intend.
- Run the documented local development stack and connect with the SDK. Verify which catalog fields are available and measure list/detail latency on a representative dataset.
- Write down assumptions: one daemon, read-only key, dataset size, expected user count, and whether access is local demo-only.

**Gate:** proceed only if local SDK-backed catalog reads work and prototype scope does not conflict with an existing company implementation.

### Days 3–5: Vertical slice

- Create an isolated dashboard prototype (prefer a separate branch or clearly named `dashboard/` area only after checking repository conventions and discussing contribution expectations).
- Implement FastAPI configuration, SDK connection lifecycle, health endpoints, catalog list/search, sequence detail, and server-rendered templates.
- Add htmx interactions for search and pagination; keep HTML usable without JavaScript where practical.

**Gate:** list and detail views work against local `mosaicod`, with clear empty/loading/error states and no secrets in the client.

### Days 6–8: Operational usefulness

- Add session and error-notification views using actual SDK fields.
- Add present-state storage summaries; do not label current snapshots as growth history.
- Add lightweight refresh/polling only where useful, with bounded request frequency and clear stale/error behavior.
- Test SDK failures, missing sequence, malformed configuration, and concurrent requests.

**Gate:** every displayed status and metric has a traceable source and honest freshness semantics.

### Days 9–10: Package and present

- Add Dockerfile and local Compose wiring for the dashboard, following repository patterns without changing daemon behavior.
- Add focused tests for routes/service mapping, template fragments, authorization/configuration, and health checks; add a smoke-test path against local services.
- Record a short demo, document setup and known limitations, and prepare a concise architecture note with next-step questions.

**Gate:** a reviewer can start the demo from documented commands, browse seeded/local data, and understand what is real versus deferred.

## Acceptance Criteria

- A non-technical user can find a sequence and answer: what is it, when was it created, how large is it, what topics/sessions does it contain, and are there recorded ingestion errors?
- No Mosaico API key or daemon credential is returned to the browser, written into the image, or logged.
- Browser routes expose only explicitly implemented operations; prototype is read-only.
- Views distinguish current values from historical trends and observed session state from live ingestion progress.
- Failures from the daemon become useful UI states rather than unhandled tracebacks.
- Local deployment is reproducible and tests do not require production credentials.

## Questions for Mosaico

1. Is dashboard development already underway, and is this role expected to extend an internal prototype or start from a blank slate?
2. Is the Python SDK the intended integration boundary, or is a dashboard-facing API planned?
3. What user authentication and tenant/sequence authorization model is expected? Are dashboard users separate from Mosaico API keys?
4. What does “monitor ingestion” mean in the product: session state, progress events, logs, or a new job API?
5. Which storage metrics and retention/history are required, and where should historical snapshots live?
6. What transfer workflows are in scope (upload, export, object-store copy), and what file sizes and interruption behavior matter?
7. What deployment environment, operational ownership, and security review process should the dashboard target?

## Outreach Approach

Send a short, specific message with the application or role reference. Mention the read-only catalog vertical slice as a hypothesis, not as a commitment or completed product. Ask for a brief conversation and permission to share a prototype. Avoid submitting a large unsolicited patch to the main repository before confirming ownership, contribution process, and current roadmap.

Suggested message:

> Hi Mosaico team, I’m interested in the dashboard role. I’ve been looking at the current repository and noticed that the Python SDK already exposes sequence metadata, sessions, storage totals, and ingestion error notifications over the existing Flight connection. I’m considering a small read-only FastAPI + server-rendered/htmx prototype around catalog discovery and operational visibility, while keeping daemon credentials server-side. Is dashboard work already in progress, and would that be a useful direction for a short prototype? I’d also be glad to discuss the intended auth, ingestion-status, and deployment boundaries before building against assumptions.

## Portfolio and Interview Story

Present the work as evidence of product and engineering judgment: chose a useful narrow workflow, reused the supported SDK boundary, did not invent progress semantics, surfaced API-key isolation risks, kept the UI progressively enhanced, and deferred file transfer until its operational contract is clear. Include screenshots or a short demo, setup instructions, tests, architecture diagram, and a candid limitations section. Do not describe a prototype as production-ready or as an official Mosaico feature.
