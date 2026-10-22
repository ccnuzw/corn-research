import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metrics = load('corn_metrics', ROOT / 'scripts/collect-production-metrics.py')
verifier = load('corn_verify', ROOT / 'scripts/verify-backup.py')


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {}
        for name in verifier.REQUIRED_FILES:
            content = name.encode()
            (self.root / name).write_bytes(content)
            self.manifest[name] = hashlib.sha256(content).hexdigest()
        self.write_manifest()

    def write_manifest(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_all_files_verified(self):
        self.assertEqual(verifier.verify(self.root), 5)

    def test_corruption_rejected(self):
        (self.root / 'postgres.dump').write_text('corrupted')
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            verifier.verify(self.root)

    def test_missing_required_artifact_rejected(self):
        self.manifest.pop('redis.rdb')
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Missing required'):
            verifier.verify(self.root)

    def test_traversal_and_symlink_rejected(self):
        self.manifest['../secret'] = 'a' * 64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Invalid manifest path'):
            verifier.verify(self.root)
        self.manifest.pop('../secret')
        self.write_manifest()
        (self.root / 'redis.rdb').unlink()
        (self.root / 'redis.rdb').symlink_to(self.root / 'postgres.dump')
        with self.assertRaisesRegex(ValueError, 'symlinked'):
            verifier.verify(self.root)


class MetricTests(unittest.TestCase):
    def response(self, compose, *args):
        if 'curl' in args:
            return '{"success":true}'
        if 'wget' in args:
            return ''
        if 'postgres' in args:
            self.assertIn('default_transaction_read_only=on', args[-3])
            return '2|1|950|45'
        if 'redis' in args:
            return 'used_memory:100\nmaxmemory:1000\n'
        self.fail(str(args))

    def test_metrics_and_completed_backups_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('good', '.incomplete-bad'):
                path = root / 'backups' / name
                path.mkdir(parents=True)
                (path / 'manifest.json').write_text('{}')
                os.utime(path / 'manifest.json', (123, 123) if name == 'good' else (999, 999))
            with patch.object(metrics, 'run', side_effect=self.response):
                text, errors = metrics.collect(root, [])
            self.assertEqual(errors, [])
            self.assertIn('corn_async_queued_jobs 2.000000', text)
            self.assertIn('corn_redis_memory_used_ratio 0.100000', text)
            self.assertIn('corn_backup_last_success_timestamp_seconds 123.000000', text)
            self.assertIn('corn_ops_collection_success 1.000000', text)

    def test_failures_not_masked_by_old_values(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(metrics, 'run', side_effect=subprocess.TimeoutExpired('secret-command', 30)):
            text, errors = metrics.collect(Path(directory), [])
        self.assertEqual(errors, ['backend', 'frontend', 'postgres', 'redis'])
        self.assertIn('corn_ops_collection_success 0.000000', text)
        self.assertIn('corn_service_up{service="postgres"} 0.000000', text)
        self.assertNotIn('secret-command', text)
        self.assertNotIn('corn_async_queued_jobs', text)


FAKE_DOCKER = r'''#!/usr/bin/env python3
import os
from pathlib import Path
import sys
args = sys.argv[1:]
if 'ps' in args:
    if os.getenv('FAKE_BACKEND_RUNNING'):
        print('fake-backend-id')
elif 'pg_dump' in ' '.join(args):
    if os.getenv('FAKE_DUMP_FAIL'):
        sys.exit(1)
    sys.stdout.buffer.write(b'PGDMP fake fixture')
elif 'pg_restore' in args:
    sys.stdin.buffer.read()
elif '--rdb' in args:
    (Path(os.environ['FAKE_ROOT']) / 'fake.rdb').write_bytes(b'REDIS fake fixture')
elif 'cp' in args:
    Path(args[-1]).write_bytes((Path(os.environ['FAKE_ROOT']) / 'fake.rdb').read_bytes())
elif 'images' in args:
    print('sha256:fixture-image')
'''


class BackupScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'data').mkdir()
        (self.root / 'data' / 'fixture.html').write_text('<html>fixture</html>')
        for name in ('backup-production.sh', 'verify-backup.py'):
            shutil.copyfile(ROOT / 'scripts' / name, self.root / 'scripts' / name)
        binary = self.root / 'bin'
        binary.mkdir()
        for name, content in (('docker', FAKE_DOCKER), ('git', '#!/bin/sh\necho fixture-commit\n')):
            path = binary / name
            path.write_text(content)
            path.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
                    'FAKE_ROOT': str(self.root), 'BACKUP_MAINTENANCE_CONFIRMED': '1'}

    def run_backup(self, **env):
        return subprocess.run(['bash', str(self.root / 'scripts/backup-production.sh')],
                              env={**self.env, **env}, text=True, capture_output=True)

    def test_success_manifest_and_lock_cleanup(self):
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshots = list((self.root / 'backups').glob('*/manifest.json'))
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(verifier.verify(snapshots[0].parent), 6)
        self.assertFalse((self.root / 'backups/.backup-lock').exists())

    def test_running_backend_rejected(self):
        result = self.run_backup(FAKE_BACKEND_RUNNING='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Stop backend', result.stderr)
        self.assertFalse(list((self.root / 'backups').glob('*/manifest.json')))

    def test_failed_dump_has_no_success_manifest(self):
        result = self.run_backup(FAKE_DUMP_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(list((self.root / 'backups').glob('*/manifest.json')))
        self.assertFalse((self.root / 'backups/.backup-lock').exists())

    def test_maintenance_confirmation_required(self):
        result = self.run_backup(BACKUP_MAINTENANCE_CONFIRMED='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Confirm all writers', result.stderr)

    def test_existing_lock_rejected(self):
        (self.root / 'backups/.backup-lock').mkdir(parents=True)
        result = self.run_backup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already running', result.stderr)


if __name__ == '__main__':
    unittest.main()
