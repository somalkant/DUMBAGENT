"""
Live Paper Trading Runner — Phase 2.5

Run this every morning before 9:15 AM:
    .\\venv\\Scripts\\python.exe run_live.py

What it does:
  1. Prevents Windows from sleeping all day
  2. Asks which broker to use (Zerodha, Groww, or any future broker)
  3. Runs the broker's authentication flow (login URL, request_token exchange, etc.)
  4. Starts the live paper trading agent — runs until 3:15 PM

Logs to logs/live_YYYY-MM-DD.log and to the terminal simultaneously.

Adding a new broker:
  - Create brokers/<name>.py inheriting BaseBroker
  - Register it in brokers/__init__.py BROKER_REGISTRY
  - The selection menu here picks it up automatically
"""

import ctypes
import logging
import sys
from datetime import date
from pathlib import Path

# ── prevent Windows sleep ─────────────────────────────────────────────────────
ES_CONTINUOUS      = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _keep_awake():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def _allow_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


# ── logging ───────────────────────────────────────────────────────────────────
def _setup_logging() -> Path:
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"live_{date.today()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return log_file


# ── broker selection ──────────────────────────────────────────────────────────
def _select_broker(log):
    """
    Ask the user which broker to use and return the configured broker instance.
    Reads available brokers from BROKER_REGISTRY — no code changes needed here
    when adding a new broker.
    """
    from brokers import get_broker, BROKER_REGISTRY

    names = list(BROKER_REGISTRY.keys())

    print()
    print("=" * 65)
    print("  Select your broker:")
    print()
    for i, name in enumerate(names, 1):
        broker = get_broker(name)
        print(f"    {i}. {broker.display_name}")
    print()
    print("=" * 65)
    print()

    while True:
        choice = input(f"  Enter number (1–{len(names)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            selected_name = names[int(choice) - 1]
            broker = get_broker(selected_name)
            log.info(f"Broker selected: {broker.display_name}")
            return broker
        print(f"  Invalid choice — enter a number between 1 and {len(names)}.")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    log_file = _setup_logging()
    log = logging.getLogger(__name__)

    _keep_awake()
    log.info("Windows sleep prevention: ON")
    log.info(f"Log file: {log_file}")

    try:
        broker       = _select_broker(log)
        access_token = broker.authenticate(log)
        _run_agent(access_token, broker.name, log)
    except KeyboardInterrupt:
        log.info("Interrupted by user — stopping agent")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        _allow_sleep()
        log.info("Windows sleep prevention: OFF")


def _run_agent(access_token: str, broker_name: str, log) -> None:
    """Hand off to the live agent with the authenticated token and broker name."""
    from live.agent import main as agent_main

    # Inject token + broker into sys.argv so agent.py's argparse picks them up
    sys.argv = ["agent.py", "--token", access_token, "--broker", broker_name]

    log.info("Starting live paper trading agent...")
    log.info("=" * 65)
    agent_main()


if __name__ == "__main__":
    main()
