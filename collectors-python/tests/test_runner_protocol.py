import json
from pathlib import Path
import subprocess
import sys
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "run_collector.py"


class RunnerProtocolTests(unittest.TestCase):
    def test_collector_logs_do_not_corrupt_json(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--collector", "mock", "--format", "json"],
            capture_output=True, text=True, check=True,
        )
        response = json.loads(result.stdout)
        self.assertTrue(response["success"])
        self.assertEqual(len(response["records"]), 10)
        self.assertIn("[mock_test]", result.stderr)
        self.assertNotIn("[mock_test]", result.stdout)

    def test_unknown_collector_returns_json_error(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--collector", "missing_collector"],
            capture_output=True, text=True, check=True,
        )
        response = json.loads(result.stdout)
        self.assertFalse(response["success"])
        self.assertEqual(response["records"], [])

    def test_list_is_json(self):
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--list"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("boyar_production", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
