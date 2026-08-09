from __future__ import annotations
import hashlib, json, sqlite3, threading, time, uuid
from pathlib import Path

class AuthorityStore:
    def __init__(self, path: str):
        self.path = path; Path(path).parent.mkdir(parents=True, exist_ok=True); self._lock = threading.RLock(); self._init()
    def _db(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None); db.row_factory = sqlite3.Row; return db
    def _init(self):
        with self._db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS budgets(task_id TEXT PRIMARY KEY, remaining INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence(ref TEXT PRIMARY KEY, kind TEXT NOT NULL, digest TEXT NOT NULL, task_id TEXT, verified INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, quality REAL NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS grants(grant_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, capability_id TEXT NOT NULL, params_hash TEXT NOT NULL, task_id TEXT, expires_at INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, payload TEXT NOT NULL, created_at INTEGER NOT NULL);
            """)
    def append_audit(self, payload: dict) -> dict:
        clean = json.loads(json.dumps(payload, sort_keys=True, default=str)); raw = json.dumps(clean, sort_keys=True, separators=(",", ":"))
        with self._lock, self._db() as db:
            row = db.execute("SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone(); prev = row[0] if row else "0"*64
            digest = hashlib.sha256((prev + raw).encode()).hexdigest(); now = int(time.time())
            cur = db.execute("INSERT INTO audit(previous_hash,entry_hash,payload,created_at) VALUES(?,?,?,?)", (prev,digest,raw,now))
            return {"seq": cur.lastrowid, "previous_hash": prev, "entry_hash": digest, "created_at": now, **clean}
    def seed_evidence(self, *, ref: str, kind: str, digest: str, task_id: str|None, quality: float, verified: bool=True):
        if not ref or len(digest) != 64: raise ValueError("evidence requires ref and sha256 digest")
        int(digest,16); q=max(0.0,min(float(quality),1.0))
        with self._db() as db: db.execute("INSERT OR REPLACE INTO evidence(ref,kind,digest,task_id,verified,revoked,quality,created_at) VALUES(?,?,?,?,?,?,?,?)",(ref,kind,digest,task_id,1 if verified else 0,0,q,int(time.time())))
    def evidence_quality(self, refs: list[str], *, task_id: str|None=None, allowed_kinds: list[str]|None=None) -> float:
        if not refs: return 0.0
        vals=[]
        with self._db() as db:
            for ref in refs:
                row=db.execute("SELECT * FROM evidence WHERE ref=?",(ref,)).fetchone()
                if not row or not row["verified"] or row["revoked"]: continue
                if task_id and row["task_id"] not in (None, task_id): continue
                if allowed_kinds and row["kind"] not in allowed_kinds: continue
                vals.append(float(row["quality"]))
        return sum(vals)/len(vals) if vals else 0.0
    def reserve_budget(self, task_id: str, weight: int, default_budget: int) -> int:
        with self._lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT remaining FROM budgets WHERE task_id=?",(task_id,)).fetchone(); remaining=int(row[0]) if row else default_budget
            if weight>remaining: db.execute("ROLLBACK"); raise ValueError(f"insufficient budget: needs {weight}, has {remaining}")
            new=remaining-weight; db.execute("INSERT INTO budgets(task_id,remaining) VALUES(?,?) ON CONFLICT(task_id) DO UPDATE SET remaining=excluded.remaining",(task_id,new)); db.execute("COMMIT"); return new
    def top_up(self, task_id: str, amount: int, default_budget: int) -> int:
        if amount <= 0: raise ValueError("top_up amount must be positive")
        with self._lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE"); row=db.execute("SELECT remaining FROM budgets WHERE task_id=?",(task_id,)).fetchone(); remaining=int(row[0]) if row else default_budget; new=remaining+amount
            db.execute("INSERT INTO budgets(task_id,remaining) VALUES(?,?) ON CONFLICT(task_id) DO UPDATE SET remaining=excluded.remaining",(task_id,new)); db.execute("COMMIT"); return new
    def create_grant(self, *, agent_id: str, capability_id: str, params_hash: str, task_id: str|None, ttl_seconds: int=60) -> dict:
        gid=str(uuid.uuid4()); exp=int(time.time())+ttl_seconds
        with self._db() as db: db.execute("INSERT INTO grants(grant_id,agent_id,capability_id,params_hash,task_id,expires_at) VALUES(?,?,?,?,?,?)",(gid,agent_id,capability_id,params_hash,task_id,exp))
        return {"grant_id":gid,"agent_id":agent_id,"capability_id":capability_id,"params_hash":params_hash,"task_id":task_id,"expires_at":exp}
    def consume_grant(self, grant_id: str, *, agent_id: str, capability_id: str, params_hash: str) -> bool:
        with self._lock, self._db() as db:
            db.execute("BEGIN IMMEDIATE"); row=db.execute("SELECT * FROM grants WHERE grant_id=?",(grant_id,)).fetchone()
            ok=bool(row and not row["used"] and row["expires_at"]>int(time.time()) and row["agent_id"]==agent_id and row["capability_id"]==capability_id and row["params_hash"]==params_hash)
            if ok: db.execute("UPDATE grants SET used=1 WHERE grant_id=?",(grant_id,)); db.execute("COMMIT")
            else: db.execute("ROLLBACK")
            return ok
