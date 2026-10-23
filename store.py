"""Small transactional store: SQLite locally; isolated Lakebase schema when deployed."""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_LOCK = threading.Lock()
DDL = [
    'CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, topic TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, contributor TEXT NOT NULL, status TEXT NOT NULL, reviewer TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL, supersedes TEXT)',
    'CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)',
]

_CREDENTIAL = {'token': None, 'user': None, 'expires': 0.0}
_CREDENTIAL_LOCK = threading.Lock()
CREDENTIAL_TTL = 40 * 60  # Lakebase database credentials are valid for an hour; refresh well before that.

def _lakebase_login(refresh=False):
    """Return (user, token), reusing the database credential instead of requesting one per connection."""
    with _CREDENTIAL_LOCK:
        if refresh or not _CREDENTIAL['token'] or time.monotonic() >= _CREDENTIAL['expires']:
            from databricks.sdk import WorkspaceClient
            w = WorkspaceClient() if (os.getenv('DATABRICKS_APP_NAME') or os.getenv('AGENT_JOB_RUNTIME')) else WorkspaceClient(profile=os.getenv('DATABRICKS_CONFIG_PROFILE', 'fevm'))
            credential = w.api_client.do('POST', '/api/2.0/postgres/credentials', body={'endpoint': os.environ['LAKEBASE_ENDPOINT']})
            _CREDENTIAL.update(token=credential['token'], user=os.getenv('LAKEBASE_USER') or _CREDENTIAL['user'] or w.current_user.me().user_name,
                               expires=time.monotonic() + CREDENTIAL_TTL)
        return _CREDENTIAL['user'], _CREDENTIAL['token']

def _lakebase_connect():
    import psycopg
    from psycopg.rows import dict_row
    for attempt in (0, 1):
        user, token = _lakebase_login(refresh=attempt == 1)
        try:
            return psycopg.connect(host=os.environ['LAKEBASE_HOST'], dbname=os.getenv('LAKEBASE_DB', 'pmt'), user=user, password=token, sslmode='require', connect_timeout=15, row_factory=dict_row)
        except psycopg.OperationalError:
            # A revoked or expired credential: fetch a fresh one once before giving up.
            if attempt: raise

@contextmanager
def connection():
    if os.getenv('LAKEBASE_HOST'):
        with _lakebase_connect() as db:
            db.execute('SET search_path TO knowledge_agent')
            yield Adapter(db, True)
    else:
        if os.getenv('DATABRICKS_APP_NAME'):
            raise RuntimeError('Deployment requires durable LAKEBASE_HOST storage; refusing ephemeral SQLite.')
        path = Path(os.getenv('KNOWLEDGE_DB', 'knowledge.sqlite'))
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            db = sqlite3.connect(path, timeout=15)
            db.row_factory = sqlite3.Row
            try:
                yield Adapter(db, False)
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

class Adapter:
    def __init__(self, db, postgres):
        self.db, self.postgres = db, postgres
    def execute(self, sql, args=()):
        return self.db.execute(sql.replace('?', '%s') if self.postgres else sql, args)
    def all(self, sql, args=()):
        return [dict(r) for r in self.execute(sql, args).fetchall()]
    def one(self, sql, args=()):
        row = self.execute(sql, args).fetchone()
        return dict(row) if row else None

def init():
    with connection() as db:
        if db.postgres:
            db.execute('SET search_path TO knowledge_agent')
        for sql in DDL:
            db.execute(sql)
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_approved_topic ON memories(topic) WHERE status='approved'")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_pending_topic ON memories(topic) WHERE status='pending'")
