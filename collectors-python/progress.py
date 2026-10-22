"""Opt-in stderr events, separate from the stdout record JSON protocol."""
import json
import os
import sys


def report_progress(phase, completed=0, total=0, **details):
    if os.getenv("CORN_PROGRESS_ENABLED") != "1":
        return
    event = {"phase": phase, "completed": completed, "total": total, **details}
    print("CORN_PROGRESS " + json.dumps(event, ensure_ascii=False), file=sys.stderr, flush=True)
