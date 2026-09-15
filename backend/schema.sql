PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS investigations (
 id TEXT PRIMARY KEY, original_input TEXT NOT NULL, normalized_claim TEXT NOT NULL,
 verdict TEXT NOT NULL, confidence TEXT NOT NULL, created_at TEXT NOT NULL,
 is_demo INTEGER NOT NULL CHECK(is_demo IN (0,1)), report_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_investigations_created ON investigations(created_at DESC);
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, domain TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
 investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
 node_id TEXT NOT NULL, source_id INTEGER REFERENCES sources(id), title TEXT NOT NULL,
 publisher TEXT NOT NULL, published_at TEXT, source_type TEXT NOT NULL, stance TEXT NOT NULL,
 confidence REAL, excerpt TEXT NOT NULL, PRIMARY KEY(investigation_id,node_id)
);
CREATE TABLE IF NOT EXISTS graph_nodes (
 investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
 node_id TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(investigation_id,node_id)
);
CREATE TABLE IF NOT EXISTS graph_edges (
 investigation_id TEXT NOT NULL, source_node TEXT NOT NULL, target_node TEXT NOT NULL,
 relationship TEXT NOT NULL, is_inferred INTEGER NOT NULL CHECK(is_inferred IN (0,1)),
 proof TEXT NOT NULL, PRIMARY KEY(investigation_id,source_node,target_node,relationship),
 FOREIGN KEY(investigation_id,source_node) REFERENCES graph_nodes(investigation_id,node_id),
 FOREIGN KEY(investigation_id,target_node) REFERENCES graph_nodes(investigation_id,node_id)
);
CREATE TABLE IF NOT EXISTS fact_checks (
 id INTEGER PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
 publisher TEXT NOT NULL, rating TEXT NOT NULL, url TEXT, reviewed_claim TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_checks_investigation ON fact_checks(investigation_id);
