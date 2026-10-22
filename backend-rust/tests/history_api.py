"""Live history API tests; temporary adapters/records are deleted via cascade."""
import json
import os
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

BASE = os.environ.get("CORN_API_BASE_URL", "http://localhost:18000")


def request(path, method="GET", body=None):
    req = Request(BASE + path, method=method, headers={"Content-Type": "application/json"},
                  data=json.dumps(body).encode() if body is not None else None)
    try:
        response = urlopen(req, timeout=30)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return response.code, payload


class HistoryApiTests(unittest.TestCase):
    def setUp(self):
        self.adapter = "test_history_" + uuid4().hex[:12]
        status, body = request("/api/adapters", "POST", {
            "id": self.adapter, "name": "Isolated history regression", "source_id": "boyar",
            "script_file": "mock", "topic_name": "test_history",
        })
        self.assertIn(status, (200, 201), body)
        self.addCleanup(request, "/api/adapters/" + self.adapter, "DELETE")

    def runs(self, suffix=""):
        return request(f"/api/adapters/{self.adapter}/runs" + suffix)

    def run_and_wait(self):
        status, body = request(f"/api/adapters/{self.adapter}/run", "POST")
        self.assertEqual(status, 200, body)
        run_id = body["data"]["run_id"]
        for _ in range(100):
            status, body = self.runs()
            self.assertEqual(status, 200)
            run = next((r for r in body["data"] if r["id"] == run_id), None)
            if run and run["status"] != "running":
                return run
            time.sleep(0.1)
        self.fail("Run did not complete")

    def test_empty_existing_adapter_and_unknown_adapter(self):
        status, body = self.runs()
        self.assertEqual(status, 200)
        self.assertEqual(body["data"], [])
        self.assertEqual(request("/api/adapters/__not_exists__/runs")[0], 404)

    def test_pagination_and_validation(self):
        self.run_and_wait()
        self.run_and_wait()
        status, body = self.runs("?limit=1")
        self.assertEqual(status, 200)
        first = body["data"][0]
        status, body = self.runs("?limit=1&offset=1")
        self.assertEqual(status, 200)
        second = body["data"][0]
        self.assertNotEqual(first["id"], second["id"])
        self.assertGreaterEqual(first["started_at"], second["started_at"])
        for value, expected in [("0", 400), ("101", 400), ("-1", 400), ("no", 400)]:
            status, _ = self.runs("?limit=" + value)
            self.assertEqual(status, expected)

    def test_success_counts_and_adapter_stats(self):
        run = self.run_and_wait()
        self.assertEqual(run["status"], "success")
        self.assertIsNotNone(run["completed_at"])
        self.assertEqual(run["records_collected"], 10)
        self.assertEqual(run["new_records"] + run["duplicate_records"], 10)
        self.assertEqual(run["failed_records"], 0)
        status, body = request("/api/adapters/" + self.adapter)
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["total_runs"], 1)
        self.assertEqual(body["data"]["successful_runs"], 1)

    def test_failure_is_recorded(self):
        status, _ = request("/api/adapters/" + self.adapter, "PUT", {"script_file": "__invalid_script__"})
        self.assertEqual(status, 200)
        run = self.run_and_wait()
        self.assertEqual(run["status"], "failed")
        self.assertIsNotNone(run["completed_at"])
        self.assertIn("Unknown collector", run["error_message"])
        status, body = request("/api/adapters/" + self.adapter)
        self.assertEqual(body["data"]["failed_runs"], 1)

    def test_synchronous_collector_also_records_history(self):
        # Keep mock uniquely mapped to its real adapter, excluding this temporary adapter.
        request("/api/adapters/" + self.adapter, "PUT", {"script_file": "__unused__"})
        status, body = request("/api/collectors/run", "POST", {"collector_name": "mock"})
        self.assertEqual(status, 200, body)
        run_id = body["data"]["run_id"]
        status, history = request("/api/adapters/adapter_mock_test/runs?limit=100")
        self.assertEqual(status, 200)
        run = next(r for r in history["data"] if r["id"] == run_id)
        self.assertEqual(run["records_collected"], 10)
        self.assertEqual(run["new_records"], 0)  # Legacy API remains fetch-only.
        self.assertEqual(run["status"], "success")
        status, history = request("/api/collectors/mock/history?limit=100")
        self.assertEqual(status, 200)
        self.assertIn(run_id, [r["id"] for r in history["data"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
