#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from .ht import HTProcess, run
from .keys import Press

# Constants
DEFAULT_ROWS = 20
DEFAULT_COLS = 50
DEFAULT_LOG_LEVEL = "WARNING"
DEFAULT_DELIMITER = ","
DEFAULT_SLEEP_AFTER_KEYS = 0.05
DEFAULT_SLEEP_AFTER_START = 0.1
SNAPSHOT_SEPARATOR = "----"

DEFAULTS: Dict[str, Union[int, str, float]] = {
    "rows": DEFAULT_ROWS,
    "cols": DEFAULT_COLS,
    "log_level": DEFAULT_LOG_LEVEL,
    "delimiter": DEFAULT_DELIMITER,
    "sleep_after_keys": DEFAULT_SLEEP_AFTER_KEYS,
    "sleep_after_start": DEFAULT_SLEEP_AFTER_START,
}


def send_keys_to_process(proc: HTProcess, keys_str: str, delimiter: str, logger: logging.Logger) -> None:
    """
    Send a sequence of keys to the subprocess.

    If it's something like "Escape" or "C-a" or something else in keys.py send
    the indicated key (or combination thereof). Otherwise, treat each character
    in the string like a separate keypress.
    """

    logger.debug(f"Parsing and sending keys: {keys_str}")
    for key_str in keys_str.split(delimiter):
        key_str = key_str.strip()
        if not key_str:
            continue

        logger.debug(f"Sending key: {key_str!r}")

        if proc.subprocess_exited:
            logger.warning(f"Subprocess has exited, cannot send keys: {key_str}")
            return

        try:
            special_key = next(
                (press_key for press_key in Press if press_key.value == key_str or press_key.name == key_str.upper()),
                None,
            )

            proc.send_keys(special_key if special_key else key_str)
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
        except Exception as e:
            logger.warning(f"Failed to send keys '{key_str}': {e}")
            return


def take_and_print_snapshot(proc: HTProcess, logger: logging.Logger) -> None:
    """Take a snapshot of the headless terminal and print it to stdout."""
    logger.debug("Taking snapshot...")

    try:
        snapshot = proc.snapshot()

        for line in snapshot.text.split("\n"):
            print(line.rstrip())

        print(SNAPSHOT_SEPARATOR)
    except RuntimeError as e:
        if "ht process has exited" in str(e):
            logger.warning("ht process has exited, cannot take snapshot")
        else:
            logger.warning(f"Failed to take snapshot: {e}")
        print(SNAPSHOT_SEPARATOR)
    except Exception as e:
        logger.warning(f"Failed to take snapshot: {e}")
        print(SNAPSHOT_SEPARATOR)


class OrderedAction(argparse.Action):
    """Custom action to preserve order of -k and -s options."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: Optional[str] = None,
    ) -> None:
        if not hasattr(namespace, "ordered_actions"):
            setattr(namespace, "ordered_actions", [])

        if option_string in ["-k", "--keys"]:
            namespace.ordered_actions.append(("keys", values))
        elif option_string in ["-s", "--snapshot"]:
            namespace.ordered_actions.append(("snapshot", None))


def parse_interleaved_args() -> Tuple[argparse.Namespace, List[Tuple[str, Optional[str]]], List[str]]:
    """Parse arguments allowing interleaved -k/--keys and -s/--snapshot options."""
    parser = argparse.ArgumentParser(
        description="Run a command with ht terminal emulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m htty.cli -- echo hello
  python -m htty.cli -k "hello,Enter" -s -- vim
  python -m htty.cli -r 30 -c 80 -s -k "ihello,Escape" -s -- vim

The -k/--keys and -s/--snapshot options can be used multiple times and will be processed in order.
        """.strip(),
    )

    parser.add_argument(
        "-r",
        "--rows",
        type=int,
        default=DEFAULT_ROWS,
        help=f"Number of terminal rows (default: {DEFAULT_ROWS})",
    )
    parser.add_argument(
        "-c",
        "--cols",
        type=int,
        default=DEFAULT_COLS,
        help=f"Number of terminal columns (default: {DEFAULT_COLS})",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        help=f"Log level (default: {DEFAULT_LOG_LEVEL})",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=DEFAULT_DELIMITER,
        help=f"Delimiter for parsing keys (default: '{DEFAULT_DELIMITER}')",
    )
    parser.add_argument(
        "-k",
        "--keys",
        metavar="KEYS",
        action=OrderedAction,
        help=(
            "Send keys to the terminal. KEYS is a comma-separated list (default delimiter). Can be used multiple times."
        ),
    )
    parser.add_argument(
        "-s",
        "--snapshot",
        action=OrderedAction,
        nargs=0,
        help="Take a snapshot of terminal output. Can be used multiple times.",
    )
    parser.add_argument(
        "command",
        nargs="*",
        metavar="-- COMMAND [ARGS...]",
        help="Command to run (must be preceded by --)",
    )

    # Find the -- separator
    try:
        dash_dash_idx = sys.argv.index("--")
        args_before_command = sys.argv[1:dash_dash_idx]
        command = sys.argv[dash_dash_idx + 1 :]
    except ValueError:
        if "--help" in sys.argv or "-h" in sys.argv:
            args_before_command = sys.argv[1:]
            command = []
        else:
            parser.error("No command specified after --")

    # Parse all arguments
    args = parser.parse_args(args_before_command)

    if not command and not any(arg in sys.argv for arg in ["--help", "-h"]):
        parser.error("No command specified after --")

    # Get the ordered actions, defaulting to empty list if none
    actions = getattr(args, "ordered_actions", [])

    return args, actions, command


def main() -> None:
    """Main CLI function."""
    try:
        basic_args, actions, command = parse_interleaved_args()
    except SystemExit:
        return  # argparse handled help or error

    if not command:
        return  # Help was shown

    # Set up logging
    try:
        numeric_level = getattr(logging, basic_args.log_level.upper())
    except AttributeError:
        print(f"Invalid log level: {basic_args.log_level}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(level=numeric_level, format="%(levelname)s: %(message)s", stream=sys.stderr)
    logger = logging.getLogger(__name__)

    try:
        # Run the command
        proc = run(" ".join(command), rows=basic_args.rows, cols=basic_args.cols)
        time.sleep(float(DEFAULTS["sleep_after_start"]))  # Let command start

        # Process actions in order
        for action_type, action_value in actions:
            if action_type == "keys":
                send_keys_to_process(proc, action_value or "", basic_args.delimiter, logger)
                time.sleep(float(DEFAULTS["sleep_after_start"]))
            elif action_type == "snapshot":
                take_and_print_snapshot(proc, logger)

        # Take a final snapshot if none were explicitly requested
        if not any(action_type == "snapshot" for action_type, _ in actions):
            take_and_print_snapshot(proc, logger)

        # Now exit the ht process cleanly (only if it's still running)
        if proc.ht_proc.poll() is None:
            proc.exit()
        else:
            logger.debug("ht process already exited")

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli() -> None:
    """Entry point for the CLI."""
    main()


if __name__ == "__main__":
    cli()
