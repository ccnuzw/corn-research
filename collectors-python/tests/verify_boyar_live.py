"""Bounded live-site verification. Advances the real Boyar Redis checkpoint."""
import argparse
import json
import logging
from pathlib import Path
import sys
import time
from unittest.mock import patch
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import BoyarConfig
from collectors.boyar_production import BoyarProductionCollector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-limit", type=int, default=2)
    parser.add_argument("--data-dir", default="/app/data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    config = BoyarConfig(scan_limit=args.scan_limit)
    initial = BoyarProductionCollector(config=config)
    before = initial.redis_client.get(config.cursor_key)
    initial.redis_client.close()
    report = {"mode": "real-site-and-redis", "cursor_key": config.cursor_key,
              "before": before, "runs": []}
    real_open = urllib.request.urlopen
    for run_no in range(1, 3):
        requests = []

        def observed_open(req, **kwargs):
            requests.append({"url": req.full_url, "at": time.monotonic()})
            return real_open(req, **kwargs)

        collector = BoyarProductionCollector(config=config, data_dir=args.data_dir)
        try:
            start = collector._get_cursor()
            with patch("urllib.request.urlopen", side_effect=observed_open):
                records = collector.collect(max_items=args.scan_limit)
            samples = []
            for record in records:
                archive = record.metadata["html_path"]
                with open(archive, "rt", encoding="utf-8") as f:
                    assert str(int(record.value)) in f.read(), "Value missing from HTML"
                samples.append({"article_id": record.metadata["article_id"],
                                "business_date": record.business_date, "value": record.value,
                                "unit": record.unit, "source_url": record.source_url,
                                "html_path": archive})
            after = collector.redis_client.get(config.cursor_key)
            if requests:
                assert requests[0]["url"].endswith(f"/{start}.html")
            gaps = [round(b["at"] - a["at"], 3) for a, b in zip(requests, requests[1:])]
            report["runs"].append({"run": run_no, "start_id": start,
                                   "requested_ids": [int(r["url"].rsplit("/", 1)[1].split(".")[0])
                                                     for r in requests],
                                   "request_gaps_seconds": gaps, "records": samples,
                                   "cursor_after": after})
            if after is not None:
                assert collector._get_cursor() == int(after) + 1
        finally:
            collector.redis_client.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
