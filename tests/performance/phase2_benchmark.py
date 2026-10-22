#!/usr/bin/env python3
"""Bounded local HTTP benchmark; never clears caches or resets collector cursors."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import http.client
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import threading
import time
from urllib.parse import urlsplit


ENDPOINTS = [
    '/health', '/api/sources', '/api/adapters', '/api/data/latest?limit=100',
    '/api/data/latest?topic=shandong_arrivals&limit=100', '/api/data/stats',
    '/api/adapters/adapter_sina_spot/runs?limit=20',
    '/api/adapters/adapter_sina_spot/records?limit=100',
]


def percentile(values, percent):
    """Nearest-rank percentile, including the slowest sample in small p99 sets."""
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * percent / 100) - 1)]


def summarize(samples, elapsed):
    times = [s['ms'] for s in samples]
    successes = sum(s['ok'] for s in samples)
    return {
        'requests': len(samples), 'successes': successes,
        'errors': len(samples) - successes,
        'status_counts': dict(Counter(str(s['status']) for s in samples)),
        'elapsed_seconds': round(elapsed, 6),
        'successful_requests_per_second': round(successes / elapsed, 2),
        'latency_ms_all_requests': {
            'min': round(min(times), 3), 'mean': round(statistics.mean(times), 3),
            'p50': round(percentile(times, 50), 3),
            'p95': round(percentile(times, 95), 3),
            'p99': round(percentile(times, 99), 3), 'max': round(max(times), 3),
        },
        'error_examples': [s for s in samples if not s['ok']][:5],
    }


class Client:
    def __init__(self, base):
        parsed = urlsplit(base)
        if parsed.scheme != 'http' or parsed.path not in ('', '/'):
            raise ValueError('Use an http://host:port base URL without a path')
        self.host, self.port = parsed.hostname, parsed.port or 80
        self.connection = None

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def request(self, path, method='GET', body=None, expected=200, timeout=10):
        if self.connection is None:
            self.connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        start = time.perf_counter()
        payload, error, status = None, None, 0
        try:
            self.connection.request(method, path, body=json.dumps(body) if body is not None else None,
                                    headers={'Content-Type': 'application/json'})
            response = self.connection.getresponse()
            status = response.status
            payload = json.loads(response.read())
            ok = status == expected and payload.get('success') is (expected < 400)
        except Exception as exc:
            ok, error = False, f'{type(exc).__name__}: {exc}'
            self.close()
        sample = {'ms': (time.perf_counter() - start) * 1000, 'status': status, 'ok': ok}
        if not ok:
            sample['error'] = error or str(payload)[:500]
        return sample, payload


def load(base, workers, requests, paths):
    ready = threading.Barrier(workers)

    def worker(index):
        client, samples = Client(base), []
        try:
            ready.wait(timeout=30)
            for number in range(index, requests, workers):
                sample, _ = client.request(paths[number % len(paths)])
                samples.append(sample)
            return samples
        finally:
            client.close()
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        samples = [sample for batch in pool.map(worker, range(workers)) for sample in batch]
    result = summarize(samples, time.perf_counter() - start)
    result['workers'] = workers
    return result


def soak(base, seconds):
    client, samples = Client(base), []
    start = time.perf_counter()
    try:
        while time.perf_counter() - start < seconds:
            sample, _ = client.request(ENDPOINTS[len(samples) % len(ENDPOINTS)])
            samples.append(sample)
            # Bounded 20 requests/s stability sample, not a saturation test.
            time.sleep(max(0, start + len(samples) * .05 - time.perf_counter()))
    finally:
        client.close()
    return summarize(samples, time.perf_counter() - start)


def docker(*args):
    return subprocess.check_output(['docker', *args], stderr=subprocess.STDOUT, text=True)


def log_volume(since):
    text = docker('logs', '--since', since, 'corn_backend')
    return {'bytes': len(text.encode()), 'lines': len(text.splitlines()),
            'sql_query_lines': sum('sqlx::query' in line for line in text.splitlines())}


def collector_benchmark(base):
    client = Client(base)
    try:
        # A separate connection gives this deliberately long request its own timeout.
        sample, response = client.request('/api/collectors/run', 'POST',
            {'collector_name': 'sina_production'}, timeout=180)
        if not sample['ok']:
            raise RuntimeError(f'Synchronous collection failed: {sample} {response}')
        client.close()
        submit, accepted = client.request('/api/collectors/run/async', 'POST',
            {'collector_name': 'sina_production'}, expected=202)
        if not submit['ok']:
            raise RuntimeError(f'Async submission failed: {submit} {accepted}')
        job_id = accepted['data']['job_id']
        job_start = time.perf_counter()
        poll, initial = client.request('/api/jobs/' + job_id)
        if not poll['ok']:
            raise RuntimeError(initial)
        overlap, overlap_response = client.request('/api/collectors/run/async', 'POST',
            {'collector_name': 'sina_production'}, expected=409)
        if not overlap['ok']:
            raise RuntimeError(f'Expected overlap rejection: {overlap_response}')
        during = load(base, 10, 400, ENDPOINTS)
        states = [initial['data']['status']]
        while True:
            poll, payload = client.request('/api/jobs/' + job_id)
            if not poll['ok']:
                raise RuntimeError(payload)
            job = payload['data']
            states.append(job['status'])
            if job['status'] in ('succeeded', 'failed'):
                break
            if time.perf_counter() - job_start > 180:
                raise TimeoutError('Async collection still running; inspect job ' + job_id)
            time.sleep(.3)
        if job['status'] != 'succeeded':
            raise RuntimeError(job)
        return {'synchronous': {'request': sample, 'response': response},
                'asynchronous': {'submit': submit, 'job': job,
                    'observed_statuses': list(dict.fromkeys(states)),
                    'seconds_after_acceptance': round(time.perf_counter() - job_start, 3),
                    'duplicate_submission': overlap, 'reads_during_job': during}}
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://localhost:18000')
    parser.add_argument('--label', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--collect', action='store_true', help='Two sequential real Sina runs')
    parser.add_argument('--requests', type=int, default=400)
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--soak-seconds', type=int, default=30)
    args = parser.parse_args()
    if args.requests < 50 or args.rounds < 1 or args.soak_seconds < 1:
        parser.error('Use at least50 requests, at least1 round and at least1 soak second')
    state = json.loads(docker('inspect', 'corn_backend'))[0]
    env = [item for item in state['Config']['Env'] if item.startswith('RUST_LOG=')]
    result = {'label': args.label, 'started_at': datetime.now(timezone.utc).isoformat(),
              'base_url': args.base, 'python': platform.python_version(),
              'host': platform.platform(), 'image': state['Image'], 'log_config': env,
              'method': 'HTTP/1.1 keep-alive per worker; closed-loop bounded requests; no automatic retries',
              'docker_resources': docker('info', '--format', '{{.NCPU}} CPUs; {{.MemTotal}} bytes; {{.Architecture}}'),
              'resources_before': docker('stats', '--no-stream', '--format', '{{json .}}',
                                         'corn_backend', 'corn_postgres', 'corn_redis')}
    idle_start = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    time.sleep(5)
    result['idle_log'] = {**log_volume(idle_start), 'window_seconds': round(time.perf_counter()-start, 3)}
    start_logs = datetime.now(timezone.utc).isoformat()
    print('Benchmark:', args.label, flush=True)
    result['sequential'] = []
    for path in ENDPOINTS:
        warm = load(args.base, 1, 5, [path])
        if warm['errors']:
            raise RuntimeError(f'Warmup failed: {path}: {warm}')
        row = load(args.base, 1, 50, [path])
        row['path'] = path
        result['sequential'].append(row)
        print(path, row['latency_ms_all_requests'], flush=True)
    result['concurrent'] = []
    for round_id in range(args.rounds):
        for workers in (1, 10, 25, 50):
            row = load(args.base, workers, args.requests, ENDPOINTS)
            row['round'] = round_id + 1
            result['concurrent'].append(row)
            print('Concurrency', workers, 'round', round_id+1, row, flush=True)
    result['read_workload_log'] = log_volume(start_logs)
    result['stability'] = soak(args.base, args.soak_seconds)
    if args.collect:
        result['collectors'] = collector_benchmark(args.base)
    result['resources_after'] = docker('stats', '--no-stream', '--format', '{{json .}}',
                                       'corn_backend', 'corn_postgres', 'corn_redis')
    final = json.loads(docker('inspect', 'corn_backend'))[0]
    result['container_after'] = {'status': final['State']['Status'],
        'health': final['State']['Health']['Status'], 'restarts': final['RestartCount']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    assert all(row['errors'] == 0 for row in
               result['sequential'] + result['concurrent'] + [result['stability']])
    if args.collect:
        assert result['collectors']['asynchronous']['reads_during_job']['errors'] == 0
    print('Saved:', args.output, flush=True)


if __name__ == '__main__':
    main()
