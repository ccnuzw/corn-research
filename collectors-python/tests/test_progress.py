"""Progress is opt-in and must never contaminate the stdout JSON protocol."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from progress import report_progress


class ProgressTests(unittest.TestCase):
    def test_disabled_by_default(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(output):
            report_progress('scanning', 1, 2)
        self.assertEqual(output.getvalue(), '')

    def test_event_is_valid_json_on_stderr_only(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {'CORN_PROGRESS_ENABLED': '1'}), redirect_stdout(out), redirect_stderr(err):
            report_progress('scanning', 1, 2, records=1, article_id=123)
        self.assertEqual(out.getvalue(), '')
        event = json.loads(err.getvalue().removeprefix('CORN_PROGRESS '))
        self.assertEqual(event, {'phase': 'scanning', 'completed': 1, 'total': 2,
                                 'records': 1, 'article_id': 123})
