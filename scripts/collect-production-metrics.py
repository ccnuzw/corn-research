#!/usr/bin/env python3
"""Read-only probes; atomically publish Prometheus textfile metrics, no credentials."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(compose, *args):
    return subprocess.check_output(compose + list(args), text=True, timeout=30,
                                   stderr=subprocess.PIPE).strip()


def collect(root, compose):
    now = time.time()
    metrics, errors = [], []

    def emit(name, value, labels=''):
        metrics.append(f'{name}{labels} {float(value):.6f}')

    def probe(service, callback):
        try:
            callback()
            emit('corn_service_up', 1, '{service="' + service + '"}')
        except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
            # Do not include subprocess arguments or outputs (may contain secrets).
            errors.append(service)
            emit('corn_service_up', 0, '{service="' + service + '"}')

    def backend():
        payload = json.loads(run(compose, 'exec', '-T', 'backend', 'curl', '--fail',
                                 '--silent', '--max-time', '5', 'http://127.0.0.1:8000/health'))
        if payload.get('success') is not True:
            raise ValueError('health failed')

    def postgres():
        query = ("SELECT count(*) FILTER (WHERE status='queued'), "
                 "count(*) FILTER (WHERE status='running'), "
                 "COALESCE(EXTRACT(EPOCH FROM NOW()-min(created_at) FILTER (WHERE status='queued')),0), "
                 "COALESCE(EXTRACT(EPOCH FROM NOW()-min(created_at) FILTER (WHERE status='running')),0) "
                 "FROM async_jobs")
        result = run(compose, 'exec', '-T', 'postgres', 'sh', '-ec',
                     'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -F "|" -c "$1"',
                     'metrics', query)
        values = [float(value) for value in result.split('|')]
        if len(values) != 4:
            raise ValueError('unexpected query output')
        for name, value in zip(('queued_jobs', 'running_jobs', 'oldest_queued_age_seconds',
                                'oldest_running_age_seconds'), values):
            emit('corn_async_' + name, max(0, value))

    def redis():
        result = run(compose, 'exec', '-T', 'redis', 'redis-cli', '--raw', 'INFO', 'memory')
        info = dict(line.split(':', 1) for line in result.splitlines() if ':' in line)
        used, maximum = int(info['used_memory']), int(info['maxmemory'])
        if maximum <= 0:
            raise ValueError('Redis maxmemory not configured')
        emit('corn_redis_memory_used_ratio', used / maximum)

    probe('backend', backend)
    probe('postgres', postgres)
    probe('redis', redis)
    try:
        disk = shutil.disk_usage(root)
        emit('corn_disk_used_ratio', disk.used / disk.total)
    except OSError:
        errors.append('disk')
    try:
        backups = []
        for manifest in (root / 'backups').glob('*/manifest.json'):
            if manifest.parent.name.startswith('.'):
                continue
            # Timestamp comes from the completed snapshot, not a partial directory.
            backups.append(manifest.stat().st_mtime)
        emit('corn_backup_last_success_timestamp_seconds', max(backups, default=0))
    except OSError:
        errors.append('backups')
    emit('corn_ops_collection_success', not errors)
    emit('corn_ops_last_collection_timestamp_seconds', now)
    return '\n'.join(metrics) + '\n', errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', default='.env.production')
    parser.add_argument('--output', default='monitoring/textfile/corn.prom')
    args = parser.parse_args()
    os.chdir(ROOT)
    compose = ['docker', 'compose', '--env-file', args.env_file, '-f', 'docker-compose.prod.yml']
    text, errors = collect(ROOT, compose)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name('.' + output.name + f'.{os.getpid()}.tmp')
    try:
        temporary.write_text(text)
        temporary.chmod(0o644)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    if errors:
        print('Metric probe failed: ' + ', '.join(errors), file=sys.stderr)
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
