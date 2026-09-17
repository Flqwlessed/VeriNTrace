# VeriTrace 2

**Updating? Read [UPDATE-V2.md](UPDATE-V2.md). Deploying? Read [DEPLOY-VERCEL.md](DEPLOY-VERCEL.md).**

An evidence-first misinformation investigation website with an interactive citation tree, network view, source cards, publication timeline and SQLite history.

**Start here: [START-HERE.md](START-HERE.md).**

Python 3.11+ is the only requirement to run the included application. No pip packages, PostgreSQL password, npm install, frontend server or CDN is required. The TypeScript frontend has already been compiled to JavaScript in `web/assets/`.

```bash
python run.py
```

Open **http://127.0.0.1:8000**. On Windows, double-click `start-windows.bat` instead. On Linux/macOS, use `python3 run.py`.

## Included

- Three explicitly fictional, offline demonstrations.
- Live Tavily basic search with a limited Wikipedia search fallback.
- Optional Groq evidence classification with TRUE/FALSE assessment. A returned quote must exist in the actual supplied text before its stance is accepted.
- Optional Google Fact Check search, plus ClaimReview extraction from retrieved pages without an extra key.
- Up to five user-supplied article URLs, eight initial sources, four relevant citation follow-ups, and three simultaneous article downloads.
- Tree and force-directed network layouts: pan, zoom, drag, fit, reset, filters, date exploration, node panels and BFS citation-path highlighting.
- Observed hyperlinks shown separately from possible semantic relationships.
- Normalized SQLite tables, transactions, foreign keys and history. JSON snapshot supports exact report replay and export.
- Safe URL fetching with public-IP validation, pinned DNS address, redirect revalidation, byte limits and deadlines.
- Actual stage progress from the backend. A provider outage yields partial evidence rather than an invented verdict.

## What the tree proves

The graph records **available citation relationships**, not every repost on the internet. An arrow `B → A` means B links to A. The tree places cited ancestors above later branches for inspection; that does not prove that A caused B to publish. All original edges remain available, so this is a tree-style layout of a directed graph, not a claim that the underlying data is a perfect tree.

Live branches only appear when retrieved article bodies link to another retrieved source. The crawler follows up to four relevant article-body links. It does not harvest random navigation links. The possible claim connections are marked as inferred. Related sources can remain disconnected.

A complete WhatsApp/Instagram/X spread history cannot be reconstructed from public news articles alone. Deleted posts, private chats, screenshots without source URLs, sites blocking extraction and unknown dates cannot be recovered by this project. There is no fabricated "patient zero". Earliest matching evidence means the earliest dated matching source found in this bounded investigation.

## API use

Normal live investigation: at most one Tavily **basic** search, one optional Google fact-check call, and one Groq classification call for all sources. Article reads use public HTTP(S), with the raw article text included in the same basic Tavily search available as a fallback. No separate paid scraping service is used. Identical successful live investigations are cached for 15 minutes in a bounded LRU cache. Failures are not cached.

No OpenAI paid API, paid database, subscription or billing-enabled account is required. Free tiers have quotas; this app cannot guarantee that providers keep those tiers forever. Do not enable paid plans or automatic billing. See `START-HERE.md` for keys and official links.

## Evidence limitations

Groq receives the lead and a relevance-selected passage of up to about 1,800 characters for at most eight articles to limit tokens. This can omit decisive context. Validated model excerpts are limited to 45 words; initial previews are 24 words. A model can misunderstand an authentic excerpt; whitespace-normalized substring validation prevents invented quotations, not incorrect interpretation. Read original sources before relying on any assessment.

Publisher identity, timestamps and ClaimReview metadata are reported by pages or providers; they are not independently authenticated. The UI does not assign universal website truth scores. Source grouping merges matching publishers/domains, near-duplicate content conservatively, but it cannot establish independence. The interface therefore says "source groups" and does not invent an independent-source count.

The live verdict engine emits TRUE, FALSE or UNABLE TO VERIFY. A direction requires an exact/matched unambiguous professional rating from a recognized fact-check/wire publisher, a validated direct excerpt from a recognized source with stance estimate >= 0.85, or validated direct excerpts from at least two distinct source groups with estimates >= 0.75. The source-role registry is explicit in `backend/decision.py`, not a rule that a TLD is truthful. Conflicting qualifying evidence remains unresolved. These automated assessments require human review; a model may misunderstand valid quotations.

## Project layout

| File/directory | Role |
|---|---|
| `run.py` | Local HTTP routes, job state, request limits, static frontend |
| `backend/config.py` | Server-side environment settings |
| `backend/providers.py` | Search, fact-check and LLM adapters |
| `backend/net.py` | Public-only HTTP(S), TLS, DNS pinning and deadlines |
| `backend/extract.py` | HTML text, metadata and article-body citations |
| `backend/pipeline.py` | Retrieval, bounded follow-up, classification and reporting |
| `backend/provenance.py` | Observed/inferred edges and source grouping |
| `backend/decision.py` | Quote validation, claim matching and TRUE/FALSE rules |
| `api/dispatch.py`, `vercel.json` | Stateless Vercel streaming API and deployment configuration |
| `frontend/history.ts` | IndexedDB history for hosted deployments |
| `backend/structures.py` | Priority queue, adjacency graph/BFS, union-find, TTL/LRU cache |
| `backend/database.py`, `backend/schema.sql` | SQLite repository and schema |
| `frontend/` | TypeScript source split into app, report, graph, UI helpers and types |
| `web/` | Included browser-ready frontend |
| `tests/` | Offline unit and HTTP integration tests |
| `docs/ARCHITECTURE.md` | Data structures, DBMS design and explanation for your presentation |
| `docs/VALIDATION.md` | Exactly what was and was not tested |

## Editing the frontend

Only if you change TypeScript, install Node.js 24+ and run:

```bash
node build.mjs
```

This uses Node's bundled TypeScript syntax stripping; it is not a type checker. No npm dependencies are required. Refresh your browser afterward. Add a full TypeScript compiler to your development tooling if you need static type checking. The backend is intentionally Python to keep DBMS and data-structure work accessible; the UI is TypeScript as requested.

Run tests from the project folder:

```bash
python -m unittest discover -s tests -v
```

## Local scope

The local server is a single-user research MVP and intentionally binds to 127.0.0.1. Do not expose that development server publicly. The included Vercel handler instead streams each investigation in one function request; it does not keep background jobs or SQLite files between invocations. Hosted history is stored per browser in IndexedDB, without accounts or cross-device synchronization. No extra database key is needed. See `DEPLOY-VERCEL.md` for the exact setup and public deployment limits.

The existing uploaded code was inspected for failure causes. This is a clean replacement, so old virtual environments and credentials are not carried over. Do not paste keys into browser code, screenshots or a public repository. `.env` and SQLite data are ignored by Git.
