"""Verify persisted scheduler failures with an isolated, disabled test job.

Requires the local Docker/PostgreSQL stack. Production jobs are never modified.
The test job and adapter are deleted only after capturing their database evidence.
"""
import json
from pathlib import Path
import subprocess
import time
import unittest
from uuid import uuid4

from history_api import request


class SchedulerFailureTests(unittest.TestCase):
    def api(self, path, method="GET", body=None):
        status, payload = request(path, method, body)
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["success"], payload)
        return payload["data"]

    def test_error_message_persisted(self):
        suffix = uuid4().hex[:12]
        adapter = "test_scheduler_failure_" + suffix
        script = "__scheduler_failure_probe_" + suffix
        self.api("/api/adapters", "POST", {
            "id": adapter, "name": "Isolated scheduler failure probe",
            "source_id": "boyar", "script_file": script, "topic_name": "test_scheduler",
        })
        self.addCleanup(self.api, "/api/adapters/" + adapter, "DELETE")
        job = self.api("/api/scheduler/jobs", "POST", {
            "name": "Isolated scheduler failure probe", "collector_id": script,
            "cron_expression": "0 0 0 1 1 *", "enabled": False,
        })["job_id"]
        # Cleanup runs in reverse order: remove the job before its adapter.
        self.addCleanup(self.api, "/api/scheduler/jobs/" + job, "DELETE")
        execution = self.api("/api/scheduler/jobs/" + job, "POST")["execution_id"]
        for _ in range(100):
            history = self.api(f"/api/scheduler/jobs/{job}/executions?status=failed")
            row = next((x for x in history if x["id"] == execution), None)
            if row:
                break
            time.sleep(0.1)
        else:
            self.fail("Failure execution did not finalize within 10 seconds")
        self.assertEqual(row["status"], "failed")
        self.assertIn("Unknown collector", row["error_message"])
        self.assertIn(script, row["error_message"])
        self.assertIsNotNone(row["completed_at"])
        jobs = self.api("/api/scheduler/jobs")
        job_row = next(x for x in jobs if x["id"] == job)
        self.assertEqual(job_row["status"], "failed")
        self.assertEqual(job_row["last_error"], row["error_message"])
        self.assertEqual(job_row["failed_count"], 1)
        run = next(x for x in self.api(f"/api/adapters/{adapter}/runs")
                   if x["id"] == row["collection_run_id"])
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["error_message"], row["error_message"])
        # UUID parsing above prevents arbitrary SQL in the independent DB check.
        from uuid import UUID
        execution = str(UUID(execution))
        sql = f"SELECT row_to_json(e) FROM job_executions e WHERE id='{execution}'::uuid;"
        database_row = json.loads(subprocess.check_output([
            "docker", "exec", "corn_postgres", "psql", "-XAt", "-v", "ON_ERROR_STOP=1",
            "-U", "corn_user", "-d", "corn_research", "-c", sql,
        ], text=True))
        self.assertEqual(database_row["error_message"], row["error_message"])
        self.assertEqual(database_row["status"], "failed")
        evidence = {
            "test": "controlled unknown-collector failure, not a production outage",
            "execution_api": row, "job_api": job_row,
            "collection_run_api": run, "postgresql_row": database_row,
            "cleanup": "isolated job/adapter removed after evidence capture; production jobs unchanged",
        }
        path = Path(__file__).resolve().parents[2] / "docs/reports/day3-scheduler-failure-evidence.json"
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
