import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import List, Union

import pytest

src_path = Path(__file__).parent.parent / "src"

env = os.environ.copy()
if "PYTHONPATH" in env:
    env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
else:
    env["PYTHONPATH"] = str(src_path)

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    lines: List[Union[str, re.Pattern]]


def terminal_contents(
    *, actual_snapshots: str, expected_patterns: List[Pattern]
) -> bool:
    actual_lines = actual_snapshots.splitlines()

    for pattern_idx, pattern in enumerate(expected_patterns):
        if len(actual_lines) < len(pattern.lines):
            print(
                f"Pattern {pattern_idx}: Not enough actual lines. Expected {len(pattern.lines)}, got {len(actual_lines)}"
            )
            return False

        # Match each line in the pattern
        for line_idx, expected_line in enumerate(pattern.lines):
            if line_idx >= len(actual_lines):
                print(
                    f"Pattern {pattern_idx}, line {line_idx}: Actual snapshot too short"
                )
                return False

            actual_line = actual_lines[line_idx]

            if isinstance(expected_line, re.Pattern):
                # This is a compiled regex pattern
                if not expected_line.match(actual_line):
                    print(
                        f"Pattern {pattern_idx}, line {line_idx}: Regex {expected_line.pattern} failed to match '{actual_line}'"
                    )
                    return False
            else:
                # This is a string that should be matched exactly
                if expected_line != actual_line:
                    print(
                        f"Pattern {pattern_idx}, line {line_idx}: Expected '{expected_line}', got '{actual_line}'"
                    )
                    return False

        # Remove the matched lines from actual_lines for the next pattern
        actual_lines = actual_lines[len(pattern.lines) :]

    return True


def test_echo_hello():
    cmd = [
        *(sys.executable, "-m"),
        "htutil.cli",
        *("-r", "2"),
        *("-c", "10"),
        "--",
        *("echo", "hello"),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello\n\n"
    actual_output = ran.stdout.replace("----\n", "")
    assert actual_output == expected_output


def test_keys_after_subproc_exit():
    cmd = [
        *(sys.executable, "-m"),
        "htutil.cli",
        *("-r", "2"),
        *("-c", "10"),
        # echo hello will happen immediately and the subprocess will close
        # then we'll attempt to send text anyway
        *("-k", "world"),
        "--",
        *("echo", "hello"),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello\n\n----\n"
    assert ran.stdout == expected_output
    print(ran.stderr)


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
        "htutil.cli",
        *("-r", "2"),
        *("-c", "10"),
        *("-k", "world,Backspace,Enter"),
        "--",
        *(sys.executable, greeter_script),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    # Remove the separator that gets added at the end
    expected_output = "hello worl\n\n"
    actual_output = ran.stdout.replace("----\n", "")
    assert actual_output == expected_output


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
        "htutil.cli",
        "--snapshot",
        *("-k", "ihello,Escape"),
        "--snapshot",
        *("-k", ":q!,Enter"),
        "--",
        vim_path,
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)

    snapshots = ran.stdout.split("----\n")
    snapshots = [s for s in snapshots if s.strip()]
    assert len(snapshots) == 2, f"Expected 2 snapshots, got {len(snapshots)}"

    # Test first snapshot (vim opening screen)
    assert terminal_contents(
        actual_snapshots=snapshots[0],
        expected_patterns=[
            Pattern(
                lines=[
                    "",
                    "~",
                    "~",
                    "~",
                    "~               VIM - Vi IMproved",
                    "~",
                    "~                version 9.1.1336",
                    "~            by Bram Moolenaar et al.",
                    "~  Vim is open source and freely distributable",
                    "~",
                    re.compile(r"~.*"),  # Variable vim message line 1
                    re.compile(r"~.*"),  # Variable vim message line 2
                    "~",
                    "~ type  :q<Enter>               to exit",
                    "~ type  :help<Enter>  or  <F1>  for on-line help",
                    "~ type  :help version9<Enter>   for version info",
                    "~",
                    "~",
                    "~",
                    "                                0,0-1         All",
                ],
            ),
        ],
    )

    # Test second snapshot (after typing hello and pressing Escape)
    assert terminal_contents(
        actual_snapshots=snapshots[1],
        expected_patterns=[
            Pattern(
                lines=[
                    "hello",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "~",
                    "                                1,5           All",
                ],
            ),
        ],
    )
