"""Offline unit tests (no API key / network needed). Run: python -m unittest discover -s tests"""
import json
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot.agent import run_agent  # noqa: E402
from copilot.ats import ats_match, extract_keywords  # noqa: E402
from copilot.chunker import chunk_text  # noqa: E402
from copilot.tools import TOOL_SPECS, ToolBox  # noqa: E402


class FakeStore:
    def __init__(self, text=""):
        self.text = text

    def get_text(self, source=None):
        return self.text

    def search(self, query, k=4, min_similarity=0.15):
        return [{"text": "Built a RAG app", "source": "resume.txt", "page": 0, "score": 0.9}]


class TestChunker(unittest.TestCase):
    def test_chunks_respect_size(self):
        text = ("Sentence about RAG. " * 80 + "\n\n") * 5
        chunks = chunk_text(text, 800, 120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 800 + 130 for c in chunks))


class TestATS(unittest.TestCase):
    JD = "We need Python, SQL, Docker and FastAPI. Experience with prompt engineering and RAG required."

    def test_keywords_found(self):
        kws = extract_keywords(self.JD)
        for k in ("python", "sql", "docker", "fastapi", "prompt engineering", "rag"):
            self.assertIn(k, kws)

    def test_score(self):
        r = ats_match(self.JD, "I know Python and SQL and built a RAG app with prompt engineering.")
        self.assertIn("python", r["matched"])
        self.assertIn("docker", r["missing"])
        self.assertTrue(0 < r["score"] < 100)


class TestTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tb = ToolBox(FakeStore("Python SQL developer"), db_path=os.path.join(self.tmp, "t.db"))
        self.en = set(TOOL_SPECS)

    def test_job_crud(self):
        self.assertIn("Added job #1", self.tb.execute("add_job", {"company": "Acme", "role": "ML Intern"}, self.en))
        self.assertIn("Interview", self.tb.execute("update_job_status", {"job_id": 1, "status": "Interview"}, self.en))
        self.assertIn("Acme", self.tb.execute("list_jobs", {}, self.en))

    def test_destructive_blocked_then_allowed(self):
        self.tb.execute("add_job", {"company": "Acme", "role": "ML Intern"}, self.en)
        self.assertIn("BLOCKED", self.tb.execute("delete_job", {"job_id": 1}, self.en, False))
        self.assertIn("Deleted", self.tb.execute("delete_job", {"job_id": 1}, self.en, True))

    def test_validation_and_allowlist(self):
        self.assertIn("ERROR", self.tb.execute("add_job", {"company": "X", "role": "Y", "status": "Nope"}, self.en))
        self.assertIn("not available", self.tb.execute("unknown_tool", {}, self.en))
        self.assertIn("not available", self.tb.execute("list_jobs", {}, {"add_job"}))
        self.assertIn("ERROR: bad arguments", self.tb.execute("add_job", {"company": "X"}, self.en))

    def test_rag_and_ats_tools(self):
        self.assertIn("Built a RAG app", self.tb.execute("search_documents", {"query": "rag"}, self.en))
        out = json.loads(self.tb.execute("ats_keyword_match", {"job_description": "Python SQL Docker"}, self.en))
        self.assertIn("docker", out["missing"])


class TestAgentLoop(unittest.TestCase):
    @staticmethod
    def _resp(msg):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)],
                                     usage=types.SimpleNamespace(prompt_tokens=10, completion_tokens=5))

    def _client(self, responses):
        return types.SimpleNamespace(chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=lambda **k: responses.pop(0))))

    @staticmethod
    def _tool_call(name, args):
        return types.SimpleNamespace(id="c1", function=types.SimpleNamespace(name=name, arguments=json.dumps(args)))

    def test_tool_then_answer(self):
        tb = ToolBox(FakeStore("x"), db_path=os.path.join(tempfile.mkdtemp(), "t.db"))
        client = self._client([
            self._resp(types.SimpleNamespace(content="", tool_calls=[self._tool_call("search_documents", {"query": "rag"})])),
            self._resp(types.SimpleNamespace(content="You built a RAG app.", tool_calls=None))])
        events = list(run_agent(client, tb, "Career Coach", [], "What did I build?", set(TOOL_SPECS)))
        self.assertEqual([e["type"] for e in events], ["tool_call", "tool_result", "final"])
        self.assertEqual(events[-1]["steps"], 2)

    def test_max_steps_safety(self):
        tb = ToolBox(FakeStore("x"), db_path=os.path.join(tempfile.mkdtemp(), "t.db"))
        loop = [self._resp(types.SimpleNamespace(content="", tool_calls=[self._tool_call("list_jobs", {})]))
                for _ in range(3)]
        events = list(run_agent(self._client(loop), tb, "Career Coach", [], "loop", set(TOOL_SPECS), max_steps=3))
        self.assertIn("Stopped after 3 steps", events[-1]["content"])


if __name__ == "__main__":
    unittest.main()
