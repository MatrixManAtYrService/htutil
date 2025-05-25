import os
import subprocess
import sys
import tempfile
import re
from pathlib import Path
from textwrap import dedent
from typing import Union

import pytest

src_path = Path(__file__).parent.parent / "src"

env = os.environ.copy()
if "PYTHONPATH" in env:
    env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
else:
    env["PYTHONPATH"] = str(src_path)


def terminal_contents(
    actual_output: str, *expected_patterns: Union[str, re.Pattern]
) -> bool:
    """
    Check if actual terminal output matches expected patterns.

    This function:
    1. Takes the actual output as the first argument
    2. Accepts multiple expected patterns (strings or compiled regex patterns)
    3. Processes string patterns with dedent and formatting
    4. Creates a combined regex pattern that handles both literal strings and regex parts
    5. Returns True if the actual output matches the combined expected pattern
    """
    pattern_parts = []

    for pattern in expected_patterns:
        if isinstance(pattern, re.Pattern):
            # For regex patterns, use the pattern string directly
            pattern_str = pattern.pattern
            # Remove the leading/trailing whitespace that dedent would remove
            pattern_str = dedent(pattern_str)
            if pattern_str.startswith("\n"):
                pattern_str = pattern_str[1:]
            if pattern_str.endswith("\n"):
                pattern_str = pattern_str[:-1]
            pattern_parts.append(pattern_str)
        else:
            # For string patterns, escape regex special characters and process with dedent
            processed = dedent(pattern)

            # Remove one leading newline (from triple-quote format)
            if processed.startswith("\n"):
                processed = processed[1:]

            # Remove trailing newline for this part
            if processed.endswith("\n"):
                processed = processed[:-1]

            # Escape the string for regex use
            escaped = re.escape(processed)
            pattern_parts.append(escaped)

    # Join all parts with newlines and ensure final trailing newline
    combined_pattern = "\n".join(pattern_parts)
    if not combined_pattern.endswith(re.escape("\n")):
        combined_pattern = combined_pattern + re.escape("\n")

    # Use regex matching with DOTALL flag to allow . to match newlines
    return bool(re.match(combined_pattern, actual_output, re.DOTALL))


def test_echo_hello():
    cmd = [
        *(sys.executable, "-m"),
        "ht_util.cli",
        *("-r", "2"),
        *("-c", "10"),
        "--",
        *("echo", "hello"),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert ran.stdout == ("hello\n\n")


@pytest.fixture
def greeter_script():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            dedent(
                """
                name = input()
                print("hello", name)
                """
            ).encode("utf-8")
        )
        tmp_path = tmp.name

    yield tmp_path
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


def test_send_keys(greeter_script):
    cmd = [
        *(sys.executable, "-m"),
        "ht_util.cli",
        *("-r", "2"),
        *("-c", "10"),
        *("-k", "world,Backspace,Enter"),
        "--",
        *(sys.executable, greeter_script),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    assert ran.stdout == ("hello worl\n\n")


def test_vim():
    try:
        vim_path = os.environ["HTUTIL_TEST_VIM_TARGET"]
    except KeyError:
        print(
            "Please run this test in the nix devshell defined in {project_root}/nix/devshell.nix"
            "doing so will provide a specific version of vim.\n"
            "To do this, run `nix develop` at the repo root and then run the tests in that shell."
        )
        raise

    cmd = [
        *(sys.executable, "-m"),
        "ht_util.cli",
        "--snapshot",
        *("-k", "ihello,Escape"),
        "--snapshot",
        *("-k", ":q!,Enter"),
        "--",
        vim_path,
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    assert terminal_contents(
        ran.stdout,
        # part of vim's opening message changes each time
        # use a regex to exclude it from the assertion
        re.compile(
            """
        
            ~
            ~
            ~
            ~               VIM - Vi IMproved
            ~
            ~                version 9.1.1336
            ~            by Bram Moolenaar et al.
            ~  Vim is open source and freely distributable
            ~
            .*
            .*
            ~
            ~ type  :q<Enter>               to exit
            ~ type  :help<Enter>  or  <F1>  for on-line help
            ~ type  :help version9<Enter>   for version info
            ~
            ~
            ~
                                            0,0-1         All
        """
        ),
        """
        hello
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
        ~
                                        1,5           All
        """,
    )
