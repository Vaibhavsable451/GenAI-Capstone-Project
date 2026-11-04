"""Agent tools: RAG search, ATS match, job tracker (SQLite), company lookup, time.

Safety: allowlist of enabled tools, destructive tools gated, timeouts, output truncation,
errors returned to the model as text so it can recover.
"""
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from .ats import ats_match

STATUSES = ["Wishlist", "Applied", "Interview", "Offer", "Rejected"]
MAX_OUTPUT = 3000


def _spec(name, desc, props=None, required=None):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props or {}, "required": required or []}}}


TOOL_SPECS = {
    "search_documents": _spec(
        "search_documents", "Semantic search over the user's uploaded resume/JD/notes (RAG). Use before talking about their background.",
        {"query": {"type": "string"}, "k": {"type": "integer", "description": "chunks to return, default 4"}}, ["query"]),
    "ats_keyword_match": _spec(
        "ats_keyword_match", "Compare a job description to the user's resume; returns ATS score, matched and missing keywords.",
        {"job_description": {"type": "string"},
         "resume_source": {"type": "string", "description": "optional resume file name; default all documents"}},
        ["job_description"]),
    "add_job": _spec(
        "add_job", "Add a job application to the tracker.",
        {"company": {"type": "string"}, "role": {"type": "string"},
         "status": {"type": "string", "enum": STATUSES}, "notes": {"type": "string"}}, ["company", "role"]),
    "list_jobs": _spec("list_jobs", "List tracked jobs, optionally filtered by status.",
                       {"status": {"type": "string", "enum": STATUSES}}),
    "update_job_status": _spec(
        "update_job_status", "Change the status of a tracked job.",
        {"job_id": {"type": "integer"}, "status": {"type": "string", "enum": STATUSES}}, ["job_id", "status"]),
    "delete_job": _spec("delete_job", "Delete a tracked job by id. DESTRUCTIVE.",
                        {"job_id": {"type": "integer"}}, ["job_id"]),
    "company_lookup": _spec("company_lookup", "Get a short factual background of a company from Wikipedia.",
                            {"company": {"type": "string"}}, ["company"]),
    "get_current_time": _spec("get_current_time", "Current date/time in an IANA timezone (default Asia/Kolkata).",
                              {"timezone": {"type": "string"}}),
}


class ToolBox:
    def __init__(self, store, db_path: str | None = None):
        self.store = store
        self.db_path = db_path or os.getenv("CAREER_DB", "career_data.db")
        self.registry = {  # name -> (callable, destructive)
            "search_documents": (self.search_documents, False),
            "ats_keyword_match": (self.ats_keyword_match, False),
            "add_job": (self.add_job, False),
            "list_jobs": (self.list_jobs, False),
            "update_job_status": (self.update_job_status, False),
            "delete_job": (self.delete_job, True),
            "company_lookup": (self.company_lookup, False),
            "get_current_time": (self.get_current_time, False),
        }

    # ---- db ----
    def _db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, "
                     "role TEXT NOT NULL, status TEXT DEFAULT 'Wishlist', notes TEXT DEFAULT '', "
                     "created TEXT DEFAULT CURRENT_TIMESTAMP)")
        return conn

    def rows(self) -> list[dict]:
        conn = self._db()
        try:
            cur = conn.execute("SELECT id, company, role, status, notes, created FROM jobs ORDER BY id DESC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            conn.close()

    def _write(self, sql: str, params: tuple):
        conn = self._db()
        try:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    # ---- tools ----
    def search_documents(self, query: str, k: int = 4) -> str:
        hits = self.store.search(query, k=int(k))
        if not hits:
            return "No relevant content found in the uploaded documents."
        return "\n\n".join(
            f"[{h['source']}{', p.' + str(h['page']) if h['page'] else ''} | sim {h['score']:.2f}]\n{h['text']}"
            for h in hits)

    def ats_keyword_match(self, job_description: str, resume_source: str | None = None) -> str:
        resume = self.store.get_text(resume_source)
        if not resume.strip():
            return "No resume text available. Ask the user to upload and process their resume first."
        return json.dumps(ats_match(job_description, resume))

    def add_job(self, company: str, role: str, status: str = "Wishlist", notes: str = "") -> str:
        if status not in STATUSES:
            return f"ERROR: status must be one of {STATUSES}"
        cur = self._write("INSERT INTO jobs(company, role, status, notes) VALUES (?,?,?,?)",
                          (company, role, status, notes))
        return f"Added job #{cur.lastrowid}: {role} at {company} [{status}]"

    def list_jobs(self, status: str | None = None) -> str:
        rows = [r for r in self.rows() if not status or r["status"] == status]
        return "\n".join(f"#{r['id']} {r['role']} @ {r['company']} [{r['status']}] {r['notes']}" for r in rows) \
            or "No jobs tracked yet."

    def update_job_status(self, job_id: int, status: str) -> str:
        if status not in STATUSES:
            return f"ERROR: status must be one of {STATUSES}"
        cur = self._write("UPDATE jobs SET status=? WHERE id=?", (status, int(job_id)))
        return f"Job #{job_id} -> {status}" if cur.rowcount else f"Job #{job_id} not found"

    def delete_job(self, job_id: int) -> str:
        cur = self._write("DELETE FROM jobs WHERE id=?", (int(job_id),))
        return f"Deleted job #{job_id}" if cur.rowcount else f"Job #{job_id} not found"

    def company_lookup(self, company: str) -> str:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "generator": "search", "gsrsearch": company, "gsrlimit": 1,
            "prop": "extracts", "exintro": 1, "explaintext": 1, "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": "career-copilot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            pages = json.loads(r.read().decode()).get("query", {}).get("pages", {})
        if not pages:
            return "No Wikipedia result found."
        p = next(iter(pages.values()))
        return f"{p['title']}: {p.get('extract', '')[:1200]}"

    def get_current_time(self, timezone: str = "Asia/Kolkata") -> str:
        return datetime.now(ZoneInfo(timezone)).strftime(f"%A, %d %B %Y, %H:%M ({timezone})")

    # ---- safe executor ----
    def execute(self, name: str, args: dict, enabled: set[str], allow_destructive: bool = False) -> str:
        if name not in self.registry or name not in enabled:
            return f"ERROR: tool '{name}' is not available."
        fn, destructive = self.registry[name]
        if destructive and not allow_destructive:
            return "BLOCKED: this action is destructive and the user has not enabled it."
        try:
            return str(fn(**args))[:MAX_OUTPUT]
        except TypeError as e:
            return f"ERROR: bad arguments for {name}: {e}"
        except Exception as e:
            return f"ERROR running {name}: {type(e).__name__}: {e}"
