#!/usr/bin/env python3
import argparse
import logging
import sys
import time
from typing import List, Tuple

from .ht import run
from .keys import Press

DEFAULTS = {
    "rows": 20,
    "cols": 50,
    "log_level": "WARNING",
    "delimiter": ",",
    "sleep_after_keys": 0.05,
    "sleep_after_start": 0.1,
}


def send_keys_to_process(proc, keys_str: str, delimiter: str, logger):
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

        logger.debug(f"Sending key: {repr(key_str)}")

        # Check if subprocess has already exited
        if hasattr(proc, "subprocess_exited") and proc.subprocess_exited:
            logger.warning(f"Subprocess has exited, cannot send keys: {key_str}")
            return

        try:
            special_key = next(
                (
                    press_key
                    for press_key in Press
                    if press_key.value == key_str or press_key.name == key_str.upper()
                ),
                None,
            )

            proc.send_keys(special_key if special_key else key_str)
            time.sleep(DEFAULTS["sleep_after_keys"])
        except Exception as e:
            logger.warning(f"Failed to send keys '{key_str}': {e}")
            return


def take_and_print_snapshot(proc, logger):
    """Take a snapshot of the headless terminal and print it to stdout."""
    logger.debug("Taking snapshot...")

    try:
        snapshot = proc.snapshot()

        # Print each line with trimmed whitespace to stdout
        for line in snapshot.text.split("\n"):
            print(line.rstrip())

        # Print separator after snapshot
        print("----")
    except RuntimeError as e:
        if "ht process has exited" in str(e):
            logger.warning("ht process has exited, cannot take snapshot")
        else:
            logger.warning(f"Failed to take snapshot: {e}")
        # Still print the separator to maintain expected output format
        print("----")
    except Exception as e:
        logger.warning(f"Failed to take snapshot: {e}")
        # Still print the separator to maintain expected output format
        print("----")


def parse_interleaved_args() -> Tuple[
    argparse.Namespace, List[Tuple[str, str]], List[str]
]:
    """Parse arguments allowing interleaved -k and --snapshot options."""
    parser = argparse.ArgumentParser(
        description="Run a command with ht terminal emulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m htutil.cli -- echo hello
  python -m htutil.cli -k "hello,Enter" --snapshot -- vim
  python -m htutil.cli -r 30 -c 80 --snapshot -k "ihello,Escape" --snapshot -- vim

The -k and --snapshot options can be used multiple times and will be processed in order.
        """.strip(),
    )

    parser.add_argument(
        "-r",
        "--rows",
        type=int,
        default=DEFAULTS["rows"],
        help=f"Number of terminal rows (default: {DEFAULTS['rows']})",
    )
    parser.add_argument(
        "-c",
        "--cols",
        type=int,
        default=DEFAULTS["cols"],
        help=f"Number of terminal columns (default: {DEFAULTS['cols']})",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULTS["log_level"],
        help=f"Log level (default: {DEFAULTS['log_level']})",
    )
    parser.add_argument(
        "-d",
        "--delimiter",
        default=DEFAULTS["delimiter"],
        help=f"Delimiter for parsing keys (default: '{DEFAULTS['delimiter']}')",
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

    # Parse basic options
    basic_args, remaining = parser.parse_known_args(args_before_command)

    if not command and not any(arg in sys.argv for arg in ["--help", "-h"]):
        parser.error("No command specified after --")

    # Parse the interleaved -k and --snapshot options
    actions = []
    i = 0
    while i < len(remaining):
        if remaining[i] == "-k" and i + 1 < len(remaining):
            actions.append(("keys", remaining[i + 1]))
            i += 2
        elif remaining[i] == "--snapshot":
            actions.append(("snapshot", None))
            i += 1
        else:
            parser.error(f"Unknown argument: {remaining[i]}")

    return basic_args, actions, command


def main():
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

    logging.basicConfig(
        level=numeric_level, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
    logger = logging.getLogger(__name__)

    try:
        # Run the command
        proc = run(" ".join(command), rows=basic_args.rows, cols=basic_args.cols)
        time.sleep(DEFAULTS["sleep_after_start"])  # Let command start

        # Process actions in order
        for action_type, action_value in actions:
            if action_type == "keys":
                send_keys_to_process(proc, action_value, basic_args.delimiter, logger)
                time.sleep(DEFAULTS["sleep_after_start"])
            elif action_type == "snapshot":
                take_and_print_snapshot(proc, logger)

        # Take a final snapshot if none were explicitly requested
        if not any(action_type == "snapshot" for action_type, _ in actions):
            take_and_print_snapshot(proc, logger)

        # Now exit the ht process cleanly (only if it's still running)
        if proc.proc.poll() is None:
            proc.exit()
        else:
            logger.debug("ht process already exited")

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli():
    """Entry point for the CLI."""
    main()


if __name__ == "__main__":
    cli()
