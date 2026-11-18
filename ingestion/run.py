"""Run every ingestion step.

    python -m ingestion.run            # real data (needs internet)
    python -m ingestion.run --sample   # synthetic sample files, no network
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pandas as pd

from ingestion import prh, vero
from ingestion.common import log, write_raw_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="use synthetic files in sample_data/")
    parser.add_argument("--only", choices=["vero", "prh"], help="run a single source")
    args = parser.parse_args()

    steps = {"vero": vero.run, "prh": prh.run}
    for name, step in steps.items():
        if args.only and name != args.only:
            continue
        log.info("=== %s (%s) ===", name, "sample" if args.sample else "live")
        step(sample=args.sample)

    # Record the run mode so the dashboard can warn when it shows synthetic data.
    write_raw_table(
        pd.DataFrame([{
            "mode": "sample" if args.sample else "live",
            "sources": args.only or "all",
            "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }]),
        "pipeline_run",
    )


if __name__ == "__main__":
    main()
