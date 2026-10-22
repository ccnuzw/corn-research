"""Integration tests for the real Python/Rust extension (no service dependencies).

Setup: bash scripts/setup-rust-integration.sh
Run: .venv/corn-rs/bin/python tests/test_integration.py
"""

import unittest

try:
    import corn_rs
except ImportError as exc:
    raise ImportError(
        "corn_rs is unavailable in this interpreter. Run "
        "`bash scripts/setup-rust-integration.sh`, then "
        "`.venv/corn-rs/bin/python tests/test_integration.py`."
    ) from exc


class RustIntegrationTests(unittest.TestCase):
    def test_quality_score(self):
        self.assertAlmostEqual(corn_rs.calculate_quality_score(0.9, 1.0, 0.95), 0.855)

    def test_invalid_quality_score(self):
        with self.assertRaises(ValueError):
            corn_rs.calculate_quality_score(2.0, 1.0, 1.0)

    def test_process_raw_data(self):
        result = corn_rs.process_raw_data([
            {"value": 1040.0, "indicator": "arrivals"},
            {"value": 2850.0, "indicator": "spot_price"},
        ])
        self.assertTrue(result.success)
        self.assertEqual(result.processed_count, 2)
        self.assertEqual(result.message, "Processing complete")

    def test_process_filters_out_of_range_values(self):
        records = [{"value": v, "indicator": "price"}
                   for v in [-1.0, 0.0, 1.0, 99999.0, 100000.0, float("nan")]]
        self.assertEqual(corn_rs.process_raw_data(records).processed_count, 2)

    def test_missing_field_raises_python_error(self):
        for record, field in [({"indicator": "price"}, "value"),
                              ({"value": 1.0}, "indicator")]:
            with self.subTest(field=field), self.assertRaises(KeyError) as error:
                corn_rs.process_raw_data([record])
            self.assertEqual(error.exception.args[0], field)

    def test_invalid_type_raises_python_error(self):
        with self.assertRaises(TypeError):
            corn_rs.process_raw_data([{"value": "invalid", "indicator": "price"}])

    def test_deduplicate(self):
        first = {"business_date": "2026-10-20", "indicator": "price", "value": 1040.0,
                 "region": "shandong", "source_url": "https://example.org/1"}
        duplicate = dict(first, source_url="https://example.org/2")
        other = dict(first, business_date="2026-10-21")
        self.assertEqual(corn_rs.deduplicate_records([first, duplicate, other]), [first, other])

    def test_validation(self):
        valid = {"business_date": "2026-10-20", "indicator": "price", "value": 1040.0,
                 "region": "shandong", "source_url": "https://example.org/1"}
        result = corn_rs.validate_records([
            valid, dict(valid, business_date=""), dict(valid, value=-1.0),
        ])
        self.assertEqual(result, {"valid_count": 1, "invalid_count": 2})

    def test_empty_input(self):
        self.assertEqual(corn_rs.deduplicate_records([]), [])
        self.assertEqual(corn_rs.process_raw_data([]).processed_count, 0)
        self.assertEqual(corn_rs.validate_records([]), {"valid_count": 0, "invalid_count": 0})


if __name__ == "__main__":
    unittest.main(verbosity=2)
