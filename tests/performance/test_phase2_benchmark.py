import unittest
from unittest.mock import Mock, patch

from phase2_benchmark import Client, load, percentile, summarize


class BenchmarkTests(unittest.TestCase):
    def test_percentile_is_nearest_rank(self):
        self.assertEqual(percentile([4, 1, 3, 2], 50), 2)
        self.assertEqual(percentile([4, 1, 3, 2], 99), 4)

    def test_errors_remain_in_latency_and_throughput_denominator(self):
        result = summarize([{'ms': 1, 'ok': True, 'status': 200},
                            {'ms': 100, 'ok': False, 'status': 500}], 2)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(result['requests'], 2)
        self.assertEqual(result['successful_requests_per_second'], .5)
        self.assertEqual(result['latency_ms_all_requests']['p95'], 100)

    def test_transport_failure_is_recorded_not_retried(self):
        client = Client('http://localhost:18000')
        with patch('phase2_benchmark.http.client.HTTPConnection') as connection:
            connection.return_value.request.side_effect = TimeoutError('test')
            sample, _ = client.request('/health')
        self.assertFalse(sample['ok'])
        self.assertEqual(sample['status'], 0)
        self.assertIn('TimeoutError', sample['error'])
        self.assertEqual(connection.return_value.request.call_count, 1)
        connection.return_value.close.assert_called_once()

    def test_http_200_error_envelope_does_not_count_as_success(self):
        client = Client('http://localhost:18000')
        with patch('phase2_benchmark.http.client.HTTPConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 200
            response.read.return_value = b'{"success":false}'
            sample, _ = client.request('/health')
        self.assertFalse(sample['ok'])

    def test_expected_conflict_can_be_asserted_separately(self):
        client = Client('http://localhost:18000')
        with patch('phase2_benchmark.http.client.HTTPConnection') as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 409
            response.read.return_value = b'{"success":false}'
            sample, _ = client.request('/api/collectors/run/async', expected=409)
        self.assertTrue(sample['ok'])

    def test_load_does_not_drop_remainder_requests(self):
        fake = Mock()
        fake.request.return_value = ({'ms': 1, 'ok': True, 'status': 200}, {})
        with patch('phase2_benchmark.Client', return_value=fake):
            result = load('http://localhost:18000', 10, 53, ['/health'])
        self.assertEqual(result['requests'], 53)
        self.assertEqual(fake.request.call_count, 53)
        self.assertEqual(result['errors'], 0)


if __name__ == '__main__':
    unittest.main()
