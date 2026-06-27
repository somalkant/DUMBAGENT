"""
DumbAgent Test Pipeline — tests 2021-2026 with flat weights and fixed 60% win rates.

No training. No freezing. All strategy weights = 1.0 (long & short).
All lifetime win rates = 60%. No blocked strategies.

Usage:
    python run_full_pipeline.py              # run all test years
    python run_full_pipeline.py --dry-run    # print the plan without executing
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Test-only pipeline — flat weights (1.0), 60% win rates, no blocked strategies
PIPELINE = [
    ("test", 2021, None),
    ("test", 2022, None),
    ("test", 2023, None),
    ("test", 2024, None),
    ("test", 2025, None),
    ("test", 2026, None),
]


def _label(step) -> str:
    kind, year, wf = step
    if kind == "test": return f"TEST  {year}"


def _run(cmd: list[str], log_file: Path) -> int:
    """Run a subprocess, tee-ing stdout+stderr to both console and log file."""
    log.info(f"  $ {' '.join(cmd)}")
    with open(log_file, "a", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            sys.stdout.write(line)
            lf.write(line)
        proc.wait()
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="DumbAgent test pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan without executing")
    args = parser.parse_args()

    # ── logging ───────────────────────────────────────────────────────────────
    pipeline_log = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(pipeline_log, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    global log
    log = logging.getLogger(__name__)

    python = str(BASE_DIR / "venv" / "bin" / "python")
    if not Path(python).exists():
        # Windows fallback
        python = str(BASE_DIR / "venv" / "Scripts" / "python.exe")
    if not Path(python).exists():
        python = sys.executable   # use whatever python is running this script

    # ── dry run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\nDumbAgent test pipeline — execution plan:")
        print(f"{'Step':<5}  {'Action':<25}  {'Log'}")
        print("─" * 55)
        for i, step in enumerate(PIPELINE, 1):
            kind, year, wf = step
            log_name = f"testing_{year}.log"
            print(f"{i:<5}  {_label(step):<25}  {log_name}")
        print()
        return

    log.info("=" * 65)
    log.info("DUMBAGENT TEST PIPELINE STARTING")
    log.info("  weights=1.0 all strategies | winrates=60% | no blocked list")
    log.info(f"Pipeline log: {pipeline_log}")
    log.info(f"Python      : {python}")
    log.info("=" * 65)

    t_start = datetime.now()
    steps_done = 0

    for i, step in enumerate(PIPELINE, 1):
        kind, year, wf = step

        log.info("")
        log.info(f"[{i}/{len(PIPELINE)}] ── {_label(step)} ──────────────────────────────────")
        step_start = datetime.now()

        step_log = LOG_DIR / f"testing_{year}.log"
        cmd = [python, "run_testing.py", str(year)]

        # ── execute ───────────────────────────────────────────────────────────
        rc = _run(cmd, step_log)
        elapsed = datetime.now() - step_start

        if rc != 0:
            log.error(f"[{i}] FAILED with exit code {rc} after {elapsed}")
            log.error(f"     Check log: {step_log}")
            log.error("Pipeline halted.")
            sys.exit(rc)

        log.info(f"[{i}] DONE in {str(elapsed).split('.')[0]}  →  log: {step_log.name}")
        steps_done += 1

    # ── final summary ─────────────────────────────────────────────────────────
    total = datetime.now() - t_start
    log.info("")
    log.info("=" * 65)
    log.info("PIPELINE COMPLETE")
    log.info(f"Total time : {str(total).split('.')[0]}")
    log.info(f"Steps done : {steps_done}/{len(PIPELINE)}")
    log.info("")
    log.info("Outputs:")
    log.info("  data/trade_logs/paper_trades.csv  ← all paper trades 2021-2026")
    log.info("  logs/testing_<year>.log           ← per-year results")
    log.info("=" * 65)

    # ── upload results to S3 so local machine can pull them ──────────────────
    _upload_results_to_s3(python, pipeline_log)


def _upload_results_to_s3(python: str, pipeline_log: Path) -> None:
    """Sync checkpoints/ and logs/ back to S3 so results are accessible without SSH."""
    import shutil
    log.info("")
    log.info("Uploading results to S3...")

    bucket = "amzn-s3-somal-bucket"
    prefix = "dumbagent"

    # Use aws cli (already installed on EC2 via ec2_setup.sh)
    aws = shutil.which("aws")
    if not aws:
        log.warning("aws CLI not found — skipping S3 upload. Copy checkpoints/ manually via SCP.")
        log.warning("  scp -i your-key.pem ubuntu@<EC2-IP>:~/DUMBAGENT/checkpoints/ .")
        return

    dirs = [
        (str(BASE_DIR / "checkpoints"), f"s3://{bucket}/{prefix}/checkpoints/"),
        (str(LOG_DIR),                  f"s3://{bucket}/{prefix}/logs/"),
    ]
    for local_dir, s3_uri in dirs:
        cmd = [aws, "s3", "sync", local_dir, s3_uri, "--exclude", "access_token.json"]
        log.info(f"  aws s3 sync {local_dir.split('/')[-1]}/ → {s3_uri}")
        rc = _run(cmd, pipeline_log)
        if rc != 0:
            log.warning(f"  S3 upload failed for {local_dir} (exit {rc}) — results still on EC2")

    log.info("")
    log.info("Results uploaded. Pull to your local machine with:")
    log.info(f"  aws s3 sync s3://{bucket}/{prefix}/checkpoints/ checkpoints/")
    log.info(f"  aws s3 sync s3://{bucket}/{prefix}/logs/        logs/ec2/")


if __name__ == "__main__":
    main()
