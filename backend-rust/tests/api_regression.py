"""Live regression checks against a restarted backend; uses mock only for runs."""
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.environ.get("CORN_API_BASE_URL", "http://localhost:18000")
ARRIVAL_INDICATORS = {"山东到车量", "山东深加工到车量"}


def request(path, body=None, method=None):
    req = Request(
        BASE_URL + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method,
    )
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


class ApiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        status, payload = request("/health")
        assert status == 200 and payload["success"], (status, payload)
        status, payload = request("/api/data/latest?limit=10000")
        assert status == 200 and payload["success"], (status, payload)
        cls.baseline = payload["data"]

    def latest(self, **params):
        status, payload = request("/api/data/latest?" + urlencode(params))
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])
        return payload["data"]

    def test_01_json_run_route(self):
        status, payload = request("/api/collectors/run", {"collector_name": "mock"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["collector_id"], "mock")
        self.assertEqual(payload["data"]["records_collected"], 10)

    def test_02_legacy_run_route(self):
        status, payload = request("/api/collectors/mock/run", method="POST")
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])

    def test_03_legacy_body_field(self):
        status, payload = request("/api/collectors/run", {"collector_id": "mock"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])

    def test_04_invalid_run_inputs(self):
        for body, expected in [
            ({}, 422),
            ({"collector_name": " "}, 400),
            ({"collector_name": "not_a_collector"}, 400),
            ({"collector_name": "mock", "max_items": 0}, 400),
            ({"collector_name": "mock", "max_items": -1}, 422),
        ]:
            with self.subTest(body=body):
                status, _ = request("/api/collectors/run", body)
                self.assertEqual(status, expected)

    def test_05_arrivals_topic(self):
        expected = [r for r in self.baseline if r["indicator_name"] in ARRIVAL_INDICATORS]
        self.assertTrue(expected, "Seed data must include arrivals to prove positive filtering")
        actual = self.latest(topic="shandong_arrivals", limit=10000)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, self.latest(topic="corn_arrivals", limit=10000))

    def test_06_unknown_topic(self):
        self.assertEqual(self.latest(topic="__p2_missing_topic__"), [])

    def test_07_topic_and_indicator_intersection(self):
        expected = [r for r in self.baseline if r["indicator_name"] == "山东深加工到车量"]
        actual = self.latest(topic="shandong_arrivals", indicator="山东深加工到车量", limit=10000)
        self.assertEqual(actual, expected)
        self.assertEqual(self.latest(topic="shandong_arrivals", indicator="北方四港库存"), [])

    def test_08_limit_after_filtering(self):
        expected = [r for r in self.baseline if r["indicator_name"] in ARRIVAL_INDICATORS][:1]
        self.assertEqual(self.latest(topic="shandong_arrivals", limit=1), expected)

    def test_09_exact_indicator_as_topic(self):
        expected = [r for r in self.baseline if r["indicator_name"] == "北方四港库存"]
        self.assertEqual(self.latest(topic="北方四港库存", limit=10000), expected)
        self.assertEqual(self.latest(topic="north_port_inventory", limit=10000), expected)

    def test_10_unfiltered_query_unchanged(self):
        self.assertEqual(self.latest(limit=10000), self.baseline)
        for path in ["/api/sources", "/api/adapters"]:
            status, payload = request(path)
            self.assertEqual(status, 200)
            self.assertTrue(payload["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
