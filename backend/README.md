# K2KM Backend

Keyword-to-Knowledge Map — scholarly graph analysis backend.
Implements MVP Phase 1–3 of the planning report.

## Architecture (Phase 1–3)

```
Client → FastAPI → AnalysisJob (PENDING)
                       │
                       └─► Celery chain (Redis broker)
                              ├─ collect_papers  → RawPayload rows
                              ├─ process_papers  → Paper / Author / Institution / Keyword / Citation
                              └─ analyze_graphs  → GraphResult × 3 (paper / author / keyword)
                                                   + Centrality + Clusters
```

Key separations enforced by the schema:
- **Raw vs canonical**: `raw_payloads` stores verbatim API responses; canonical entities live in `papers`, `authors`, etc.
- **Display vs analytical**: display metadata (title, abstract, venue) on canonical entities; analytical metrics on `centrality_results`, `cluster_results`, `graph_*`.
- **Paper / author / keyword graphs**: three independent `GraphResult` rows per job — never a mixed graph.
- **No nationality**: `author_affiliations.country_code` is derived from institution metadata only.
- **No SCI/SSCI inference**: `papers.sci_classification` is reserved for future registry-based post-processing.
- **NTIS reserved**: schema makes no assumption about NTIS yet; will be added as an overlay layer in Phase 6.

## Stack

- Python 3.12 / FastAPI / SQLAlchemy 2.x / Alembic
- PostgreSQL 16 / Redis 7
- Celery 5 background workers
- NetworkX + python-louvain for graphs (igraph swap-in planned for Large Mode)
- OpenAlex + Semantic Scholar connectors

## Running locally

```bash
cp .env.example .env
# fill in OPENALEX_EMAIL (required for polite-pool access)
docker compose up --build
# In another terminal — run migrations:
docker compose exec api alembic upgrade head
```

API: http://localhost:8000 — Swagger UI at `/docs`.

## Endpoints (v1)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/jobs` | Create job from an explicit keyword. Enqueues `collect → process → analyze` chain. |
| POST | `/api/v1/jobs/from-query` | Create job from a **natural-language question** (parser extracts keyword + intent + year hints). |
| POST | `/api/v1/jobs/parse-query` | Preview the NL parser output without creating a job. |
| GET  | `/api/v1/jobs` | List jobs. Filter by `status`. |
| GET  | `/api/v1/jobs/{job_id}` | Job status + progress. |
| POST | `/api/v1/jobs/{job_id}/cancel` | Revoke Celery task and mark cancelled. |
| GET  | `/api/v1/jobs/{job_id}/papers` | Papers for the job, ranked by citations. |
| GET  | `/api/v1/papers/{paper_id}` | Paper detail. |
| GET  | `/api/v1/jobs/{job_id}/authors` | Authors for the job. |
| GET  | `/api/v1/authors/{author_id}` | Author detail. |
| GET  | `/api/v1/jobs/{job_id}/keywords` | Keywords for the job. |
| GET  | `/api/v1/jobs/{job_id}/graphs` | All three graphs (paper/author/keyword) for the job. |
| GET  | `/api/v1/graphs/{graph_id}` | Graph metadata + nodes + edges (pagination via `node_limit` / `edge_limit`). |
| GET  | `/api/v1/health` | Health check. |

## Job parameters

```jsonc
POST /api/v1/jobs
{
  "keyword": "foundation model",   // required
  "max_papers": 20000,             // 100–50000, default 20000
  "year_start": 2018,              // optional
  "year_end": 2025,                // optional
  "publication_types": ["journal", "conference"]  // optional, default = all
}
```

### Natural-language entry point

The analysis core is keyword-based by design (see planning report §5-1).
A thin NL layer translates questions into the same job payload:

```jsonc
POST /api/v1/jobs/from-query
{ "query": "quantum computing 분야에서 누가 잘해?" }
```

Internally this is parsed to:

```jsonc
{
  "keyword": "quantum computing",
  "intent": "author_influence",      // author_influence | paper_centrality | keyword_clusters | general
  "year_start": null,
  "year_end": null
}
```

Detected intent and the original query text are stored on `AnalysisJob.params`
so the frontend can highlight the relevant graph (author / paper / keyword)
without altering the underlying analysis.

Examples that work:

| Query | Extracted keyword | Intent | Years |
|---|---|---|---|
| `quantum computing 분야에서 누가 잘해?` | `quantum computing` | `author_influence` | – |
| `최근 5년 동안 digital twin 분야에서 어떤 논문이 중요해?` | `digital twin` | `paper_centrality` | current−4 ~ current |
| `AI governance 분야의 동향이 궁금해` | `AI governance` | `keyword_clusters` | – |
| `Who are the top researchers in foundation models?` | `foundation models` | `author_influence` | – |
| `foundation model 2018-2023 핵심 논문` | `foundation model` | `paper_centrality` | 2018 ~ 2023 |

Use `POST /api/v1/jobs/parse-query` to dry-run the parser before submitting.
If no keyword can be extracted (e.g. `누가 잘해?` alone), the endpoint returns 422.

The default parser is the dependency-free `HeuristicQueryParser`. The same
`QueryParser` protocol allows a Claude-backed parser to be swapped in later
without changing the API surface.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q tests/
```

Pure-function tests (`test_processing.py`, `test_analysis.py`) run without a database.

## Roadmap hooks left in place

- **NTIS overlay**: no schema coupling; future tables (`ntis_projects`, `ntis_institutions`, `comparative_results`) will reference `analysis_jobs.id` without mutating `papers` / `authors`.
- **Blog generation**: graph + cluster + centrality outputs are already persistable; a `blog_drafts` table can join them later.
- **Large Mode (20k–50k)**: collection batches at 500-row commits; graph builders gate co-citation / bib-coupling / co-occurrence by minimum-weight thresholds; betweenness samples nodes above 2000.
- **SCI/SSCI registry**: `papers.sci_classification` left null; post-processor will populate later.
- **Embedding similarity**: keyword/paper graphs currently use co-occurrence and citation. Embedding similarity edges can be added as new `edge_type` rows without schema changes.

## What is NOT in this phase

Per planning instructions — these are deliberately deferred:

- Frontend (Next.js)
- NTIS connector and comparative intelligence layer
- Claude orchestration / blog draft generation
- SCI/SSCI registry post-processor
- Embedding similarity edges
