import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

src_path = Path(__file__).parent.parent / "src"

env = os.environ.copy()
if "PYTHONPATH" in env:
    env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
else:
    env["PYTHONPATH"] = str(src_path)


def terminal_contents(*contents: str) -> str:
    """
    Process terminal content strings to match actual terminal output.
    
    This function:
    1. Accepts multiple content strings (useful for multiple snapshots)
    2. Removes common leading indentation from each (like dedent)
    3. Removes the extra leading newline added by triple-quote format
    4. Preserves internal empty lines including intended leading empty lines
    5. Ensures proper newlines between content blocks and at the end
    """
    processed_parts = []
    
    for content in contents:
        # Use dedent to remove common leading whitespace
        processed = dedent(content)
        
        # Remove one leading newline (from triple-quote format) but preserve 
        # any subsequent newlines that represent actual empty lines in the terminal
        if processed.startswith('\n'):
            processed = processed[1:]
        
        # Remove trailing newline for this part (we'll add them back between parts)
        if processed.endswith('\n'):
            processed = processed[:-1]
            
        processed_parts.append(processed)
    
    # Join all parts with newlines and ensure final trailing newline
    result = '\n'.join(processed_parts)
    if not result.endswith('\n'):
        result = result + '\n'
    
    return result


def test_echo_hello():
    cmd = [
        *(sys.executable, "-m"),
        "ht_util.cli",
        # *("--log-level", "DEBUG"),
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
        # *("--log-level", "DEBUG"),
        *("-r", "2"),
        *("-c", "10"),
        *("-k", "world,Backspace,Enter"),
        "--",
        *(sys.executable, greeter_script),
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    assert ran.stdout == ("hello worl\n\n")


def test_vim():
    cmd = [
        *(sys.executable, "-m"),
        "ht_util.cli",
        # *("--log-level", "DEBUG"),
        "--snapshot",
        *("-k", "ihello,Escape"),
        "--snapshot", 
        *("-k", ":q!,Enter"),
        "--",
        "vim"
    ]

    ran = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
    assert ran.stdout == terminal_contents(
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
        ~         Help poor children in Uganda!
        ~ type  :help iccf<Enter>       for information
        ~
        ~ type  :q<Enter>               to exit
        ~ type  :help<Enter>  or  <F1>  for on-line help
        ~ type  :help version9<Enter>   for version info
        ~
        ~
        ~
                                        0,0-1         All
        """,
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
        """
    )
