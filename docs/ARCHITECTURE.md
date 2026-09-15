# How to explain this project

VeriTrace retrieves sources, extracts evidence, classifies short source excerpts and records observed citations. Its tree is a visual exploration of a directed graph. It stores investigations and their evidence in SQLite so reopening a report does not call an API again.

## Data structures actually used

| Structure | Location | Purpose | Complexity |
|---|---|---|---|
| Binary max-priority heap | `backend/structures.py`, pipeline | Process user-supplied URLs first, then search relevance; prioritize a bounded citation frontier | Push/pop O(log n) |
| Hash set | Pipeline | Deduplicate canonical URLs and stop repeat fetches | Expected O(1) membership |
| Adjacency-list directed graph | `backend/provenance.py`, graph frontend | Store source-to-source and source-to-claim relationships without a dense matrix | O(V+E) storage |
| Breadth-first search with queue and visited/parent map | `frontend/graph.ts` | Find shortest observed directed citation path in the filtered view | O(V+E) |
| Union-find with path compression | `backend/structures.py`, provenance | Group common publishers, observed citation connections and highly overlapping copies to reduce double counting | Near constant amortized find with compression in practice; this implementation has no union-by-rank guarantee |
| Bounded LRU cache with expiry and lock | Pipeline/structures | Reuse successful identical investigations for 15 minutes, up to 100 entries | Expected O(1) get/put |
| Chronological ordering | Report/pipeline | Order dated evidence while keeping unknown dates explicit | O(n log n) |

The priority score reflects retrieval relevance and user-provided leads. It is not a truth score and does not prefer `.gov` just because of its suffix.

The frontend tree assigns citation ancestors to levels and puts at most four nodes across each visual row. It preserves all edges rather than discarding alternate parents. Cycles are bounded by visited sets. The network option uses repulsive forces between nodes and attractive forces along existing edges; layout forces do not create new relationships.

## DBMS design

| Table | Stored information |
|---|---|
| investigations | Original input, normalized claim, verdict, confidence, timestamp, demo flag, complete replay snapshot |
| sources | Unique canonical URL and domain |
| evidence | Per-investigation source metadata, stance, exact excerpt and classification confidence |
| graph_nodes | Per-investigation node data, including the claim node |
| graph_edges | Directed relationship, inferred flag, human-readable proof; foreign keys to graph nodes |
| fact_checks | Publisher, reviewed claim, rating and URL for each candidate |

Evidence metadata is per investigation so a changed article does not silently alter old investigations. The report JSON is a deliberate immutable replay snapshot, while relational tables support SQL joins, validation and future analysis.

Saving the investigation, evidence, nodes, edges and fact checks is a single transaction. Failed writes roll back. Parameterized statements avoid SQL injection. Foreign keys prevent dangling edges. The unique source URL prevents duplicate URL rows. An index on investigation time supports recent-history access; fact checks are indexed by investigation ID. WAL and a busy timeout support local concurrent reading/writing.

Example SQL for your presentation:

```sql
SELECT i.normalized_claim, e.title, e.stance, s.url
FROM investigations AS i
JOIN evidence AS e ON e.investigation_id = i.id
LEFT JOIN sources AS s ON s.id = e.source_id
WHERE i.id = ?;
```

Inspect a local database without installing a database server:

```bash
python -c "import sqlite3; c=sqlite3.connect('data/veritrace.db'); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"
```

## Request flow

1. Browser posts claim text and optional source URLs to `/api/investigate`.
2. Server validates input and returns a job ID immediately.
3. Browser polls `/api/jobs/{id}` for actual stage status.
4. Server retrieves search results; missing search service triggers a limited encyclopedia fallback.
5. A priority queue selects at most eight starting sources. Three workers retrieve pages. A second bounded frontier follows up to four relevant article-body citations.
6. Optional professional fact checks are combined with ClaimReview metadata found in pages.
7. Groq classifies all available evidence in one request. A returned quote must be 8–24 words and appear verbatim in the supplied evidence window. Otherwise it is rejected and the source remains context.
8. Provenance uses observed article-body hyperlinks. Exact claim wording produces an observed `repeats_claim` relation; AI semantic classification produces a visibly inferred `references` relation. A repeated claim is not necessarily endorsed.
9. Grouping reduces duplicated evidence. A conservative deterministic rule generates the preliminary verdict; the model is not asked to decide truth from its memory.
10. SQLite saves the report. The browser renders source cards, the graph, timeline, warnings and history.

The old `/api/verify` name is accepted as an alias for starting a job, but the old frontend response shape is not compatible. Use the supplied new frontend.

## API boundaries and security

Each provider adapter handles its own unavailable/invalid response. All external traffic has a deadline and size limit. DNS responses must contain only globally routable IPs; requests connect to the validated IP while preserving TLS hostname checks. Redirects are revalidated and provider POST redirects are refused. No article can instruct the server to visit an internal address.

Only static web assets are served; `.env`, database files and Python sources cannot be downloaded over HTTP. The frontend escapes text, restricts link schemes and never receives keys. The server enforces localhost Host/Origin checks and JSON requests. Rate limiting allows one new investigation every five seconds and two simultaneous jobs.

This local HTTP server is deliberately not an internet deployment platform. Authentication, per-user ownership, stronger abuse controls, robust publisher extraction, assessed test datasets, multilingual matching and social-network integrations are future work, not silently claimed features.
