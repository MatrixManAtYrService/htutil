"""
Simple test using the htutil module to make assertions about terminal output.
"""

import sys
import os
import pytest
import tempfile
from textwrap import dedent
from htutil import run, Press, ht_process


COLORED_HELLO_WORLD_SCRIPT = """
print("\\033[31mhello\\033[0m")
input()
print("\\033[32mworld\\033[0m")
input()
print("\\033[33mgoodbye\\033[0m")
"""


@pytest.fixture
def hello_world_script():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            dedent("""
                print("hello")
                input()
                print("world")
                input()
                print("goodbye")
            """).encode("utf-8")
        )
        tmp_path = tmp.name

    yield tmp_path
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def colored_hello_world_script():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(
            dedent(
                """
                print("\\033[31mhello\\033[0m")
                input()
                print("\\033[32mworld\\033[0m")
                input()
                print("\\033[33mgoodbye\\033[0m")
                """
            ).encode("utf-8")
        )
        tmp_path = tmp.name

    yield tmp_path
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


def test_hello_world_with_scrolling(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=3, cols=8)
    assert proc.snapshot().text == ("hello   \n        \n        ")

    # hello has scrolled out of view
    proc.send_keys(Press.ENTER)
    assert proc.snapshot().text == ("        \nworld   \n        ")


def test_hello_world_after_exit(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    ht = run(cmd, rows=6, cols=8)
    ht.send_keys(Press.ENTER)
    ht.send_keys(Press.ENTER)
    ht.subprocess.wait()
    assert ht.snapshot().text == (
        "hello   \n        \nworld   \n        \ngoodbye \n        "
    )

    exit_code = ht.exit()
    assert ht.subprocess.exit_code == 0
    assert exit_code == 0


def test_outputs(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    ht = run(cmd, rows=4, cols=8)
    ht.send_keys(Press.ENTER)  # First input() call
    ht.send_keys(Press.ENTER)  # Second input() call to let script finish
    # Wait for the script to complete naturally
    ht.subprocess.wait()

    # Be more tolerant of how output gets split across events
    # Just check that we got the expected content across all output events
    all_output_text = "".join(event["data"]["seq"] for event in ht.output)

    # Should contain all the expected text (now that we let it complete)
    assert "hello" in all_output_text, f"Expected 'hello' in output: {all_output_text}"
    assert "world" in all_output_text, f"Expected 'world' in output: {all_output_text}"
    assert "goodbye" in all_output_text, (
        f"Expected 'goodbye' in output: {all_output_text}"
    )

    # Should have at least some output events
    assert len(ht.output) > 0, "Should have at least one output event"

    ht.exit()  # Clean up the ht process


def test_enum_keys_interface(hello_world_script):
    """Test that the new enum keys interface works correctly."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=3, cols=8)
    proc.send_keys(Press.ENTER)

    assert proc.snapshot().text == ("        \nworld   \n        ")


def test_html_snapshot_with_colors(colored_hello_world_script):
    """Test that the new SnapshotResult provides HTML with color information."""
    cmd = f"{sys.executable} {colored_hello_world_script}"
    proc = run(cmd, rows=4, cols=8)

    snapshot = proc.snapshot()

    # Test that HTML contains the expected CSS and span for red text
    assert ".ansi31 { color: #aa0000; }" in snapshot.html
    assert '<span class="ansi31">hello</span>' in snapshot.html

    # Continue script to get green "world"
    proc.send_keys(Press.ENTER)

    snapshot2 = proc.snapshot()

    # Test that we now have green color styling too
    assert ".ansi32 { color: #00aa00; }" in snapshot2.html
    assert '<span class="ansi32">world</span>' in snapshot2.html

    # Clean up
    proc.subprocess.terminate()
    proc.subprocess.wait(timeout=1.0)
    proc.terminate()
    proc.wait(timeout=2.0)


def test_context_manager(hello_world_script):
    """Test the context manager API for automatic cleanup."""
    cmd = f"{sys.executable} {hello_world_script}"

    # Test that context manager works and cleans up automatically
    with ht_process(cmd, rows=3, cols=8) as proc:
        proc.send_keys(Press.ENTER)

        snapshot = proc.snapshot()
        assert "world" in snapshot.text


def test_exit_while_subprocess_running(hello_world_script):
    """Test that exit() works reliably even when subprocess is still running."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=4, cols=8, no_exit=True)

    # Take initial snapshot
    snapshot = proc.snapshot()
    assert "hello" in snapshot.text

    # Exit while subprocess is still waiting for input (should force termination)
    exit_code = proc.exit(timeout=5.0)

    # Should exit cleanly
    assert exit_code == 0

    # Process should be terminated
    assert proc.proc.poll() is not None, "ht process should have exited"


def test_exit_after_subprocess_finished(hello_world_script):
    """Test that exit() works when subprocess has already finished."""
    cmd = f"{sys.executable} {hello_world_script}"
    proc = run(cmd, rows=4, cols=8, no_exit=True)

    # Complete the script
    proc.send_keys(Press.ENTER)  # First input()
    proc.send_keys(Press.ENTER)  # Second input()

    # Wait for subprocess to finish
    proc.subprocess.wait(timeout=3.0)

    # Take final snapshot
    snapshot = proc.snapshot()
    assert "goodbye" in snapshot.text

    # Exit should work cleanly
    exit_code = proc.exit(timeout=5.0)
    assert exit_code == 0

    # Process should be terminated
    assert proc.proc.poll() is not None, "ht process should have exited"
