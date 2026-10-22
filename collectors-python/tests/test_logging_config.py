import io
import logging
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import BoyarConfig, collector_log_level, configure_runtime_logging


class LoggingConfigTests(unittest.TestCase):
    def test_environment_overrides_rotation(self):
        with patch.dict(os.environ, {'COLLECTOR_LOG_MAX_BYTES': '2048', 'COLLECTOR_LOG_BACKUP_COUNT': '2'}):
            config = BoyarConfig()
        self.assertEqual(config.log_max_bytes, 2048)
        self.assertEqual(config.log_backup_count, 2)

    def test_invalid_rotation_is_rejected(self):
        with patch.dict(os.environ, {'COLLECTOR_LOG_MAX_BYTES': '0'}):
            with self.assertRaises(ValueError):
                BoyarConfig()

    def test_invalid_level_is_rejected(self):
        with patch.dict(os.environ, {'COLLECTOR_LOG_LEVEL': 'VERBOSE'}):
            with self.assertRaises(ValueError):
                collector_log_level()

    def test_console_uses_stderr_utc_and_level(self):
        root = logging.getLogger()
        handlers, level = root.handlers[:], root.level
        root.handlers = []
        try:
            output, stdout = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {'COLLECTOR_LOG_LEVEL': 'WARNING'}), \
                    patch('sys.stderr', output), patch('sys.stdout', stdout):
                configure_runtime_logging()
                logging.info('hidden')
                logging.warning('visible')
            self.assertIn('Z WARNING root: visible', output.getvalue())
            self.assertNotIn('hidden', output.getvalue())
            self.assertEqual(stdout.getvalue(), '')
        finally:
            root.handlers, root.level = handlers, level


if __name__ == '__main__':
    unittest.main()
