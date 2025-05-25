#!/usr/bin/env python3
"""
Command-line interface for ht_util.

Provides a CLI wrapper around ht_util.run() that captures terminal output
and prints it to stdout with whitespace trimmed.
"""

import sys
import logging
import time
from .ht import run


def send_keys_to_process(proc, keys_str: str, delimiter: str, logger):
    """Send a sequence of keys to the process."""
    logger.debug(f"Parsing and sending keys: {keys_str}")
    key_list = keys_str.split(delimiter)

    from .keys import Press

    for key_str in key_list:
        key_str = key_str.strip()
        if not key_str:
            continue

        logger.debug(f"Sending key: {repr(key_str)}")

        # Try to find it as a Press enum value
        special_key = None
        for press_key in Press:
            if press_key.value == key_str or press_key.name == key_str.upper():
                special_key = press_key
                break

        if special_key:
            proc.send_keys(special_key)
        else:
            proc.send_keys(key_str)

        time.sleep(0.05)


def take_and_print_snapshot(proc, logger):
    """Take a snapshot and print it to stdout."""
    logger.debug("Taking snapshot...")
    snapshot = proc.snapshot()

    # Print each line with trimmed whitespace to stdout
    for line in snapshot.text.split("\n"):
        print(line.rstrip())


def parse_interleaved_args():
    """Parse arguments allowing interleaved -k and --snapshot options."""
    import argparse

    # Basic argument parser for the simple options
    parser = argparse.ArgumentParser(
        description="Run a command with ht terminal emulation", add_help=False
    )
    parser.add_argument(
        "-r", "--rows", type=int, default=20, help="Number of terminal rows"
    )
    parser.add_argument(
        "-c", "--cols", type=int, default=50, help="Number of terminal columns"
    )
    parser.add_argument("--log-level", default="WARNING", help="Log level")
    parser.add_argument(
        "-d", "--delimiter", default=",", help="Delimiter for parsing keys"
    )
    parser.add_argument("--help", action="store_true", help="Show help and exit")

    # Find the -- separator
    try:
        dash_dash_idx = sys.argv.index("--")
        args_before_command = sys.argv[1:dash_dash_idx]
        command = sys.argv[dash_dash_idx + 1 :]
    except ValueError:
        # No -- found, check if it's just a help request
        if "--help" in sys.argv:
            args_before_command = sys.argv[1:]
            command = []
        else:
            print("Error: No command specified after --", file=sys.stderr)
            sys.exit(1)

    # Parse basic options
    basic_args, remaining = parser.parse_known_args(args_before_command)

    if basic_args.help:
        print("""Usage: python -m ht_util.cli [OPTIONS] [-k KEYS] [--snapshot] ... -- COMMAND [ARGS...]

Options:
  -r, --rows INTEGER     Number of terminal rows [default: 10]
  -c, --cols INTEGER     Number of terminal columns [default: 40]
  --log-level TEXT       Log level [default: WARNING]
  -d, --delimiter TEXT   Delimiter for parsing keys [default: ,]
  -k TEXT                Keys to send
  --snapshot             Take and print a snapshot
  --help                 Show this message and exit

The -k and --snapshot options can be used multiple times and will be processed in order.
""")
        sys.exit(0)

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
            print(f"Error: Unknown argument: {remaining[i]}", file=sys.stderr)
            sys.exit(1)

    return basic_args, actions, command


def main():
    """Main CLI function."""
    basic_args, actions, command = parse_interleaved_args()

    if not command:
        print("Error: No command specified after --", file=sys.stderr)
        sys.exit(1)

    # Set up logging
    numeric_level = getattr(logging, basic_args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {basic_args.log_level}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=numeric_level, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
    logger = logging.getLogger(__name__)

    try:
        # Run the command
        command_str = " ".join(command)
        proc = run(command_str, rows=basic_args.rows, cols=basic_args.cols)
        time.sleep(0.1)  # Let command start

        # Process actions in order
        for action_type, action_value in actions:
            if action_type == "keys":
                send_keys_to_process(proc, action_value, basic_args.delimiter, logger)
                time.sleep(0.1)
            elif action_type == "snapshot":
                take_and_print_snapshot(proc, logger)

        # If no snapshots were taken, take one at the end
        if not any(action_type == "snapshot" for action_type, _ in actions):
            proc.subprocess.wait()  # Wait for completion
            take_and_print_snapshot(proc, logger)

        proc.exit()

    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cli():
    """Entry point for the CLI."""
    main()


if __name__ == "__main__":
    cli()
