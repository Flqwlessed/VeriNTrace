import json
import sqlite3
from .config import DB_PATH, ROOT


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript((ROOT / 'backend' / 'schema.sql').read_text())

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute('PRAGMA foreign_keys=ON')
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, report):
        with self.connect() as conn:
            conn.execute('INSERT INTO investigations VALUES (?,?,?,?,?,?,?,?)', (report['id'], report['originalInput'], report['claim'], report['verdict'], report['confidence'], report['createdAt'], int(report['demo']), json.dumps(report)))
            for source in report['evidence']:
                source_id = None
                if source['url']:
                    conn.execute('INSERT OR IGNORE INTO sources(url,domain) VALUES (?,?)', (source['url'], source['domain']))
                    source_id = conn.execute('SELECT id FROM sources WHERE url=?', (source['url'],)).fetchone()[0]
                conn.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)', (report['id'], source['id'], source_id, source['title'], source['publisher'], source['publishedAt'], source['sourceType'], source['stance'], source['confidence'], source['excerpt']))
            for node in report['graph']['nodes']:
                conn.execute('INSERT INTO graph_nodes VALUES (?,?,?)', (report['id'], node['id'], json.dumps(node)))
            for edge in report['graph']['edges']:
                conn.execute('INSERT INTO graph_edges VALUES (?,?,?,?,?,?)', (report['id'], edge['source'], edge['target'], edge['relationship'], int(edge['isInferred']), edge['proof']))
            for item in report['factChecks']:
                conn.execute('INSERT INTO fact_checks(investigation_id,publisher,rating,url,reviewed_claim) VALUES (?,?,?,?,?)', (report['id'], item['publisher'], item['rating'], item['url'], item['reviewedClaim']))

    def get(self, investigation_id):
        with self.connect() as conn:
            row = conn.execute('SELECT report_json FROM investigations WHERE id=?', (investigation_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def history(self):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute('SELECT i.id,i.normalized_claim AS claim,i.verdict,i.created_at AS createdAt,i.is_demo AS demo,COUNT(e.node_id) AS sourceCount FROM investigations i LEFT JOIN evidence e ON e.investigation_id=i.id GROUP BY i.id ORDER BY i.created_at DESC LIMIT 50')]
