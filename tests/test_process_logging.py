"""
Test process termination logging to ensure correct messages appear.
"""

import logging
import sys
import tempfile
from io import StringIO
from textwrap import dedent
from typing import Any, Callable, Tuple

from htty import ht_process, run


def capture_debug_logs(func: Callable[[], Any]) -> Tuple[Any, str]:
    """Decorator to capture debug logs from a function."""
    # Create a string buffer to capture logs
    log_capture = StringIO()

    # Create a handler that writes to our buffer
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # Get the htty logger and add our handler
    logger = logging.getLogger("htty.ht")
    original_level = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    try:
        # Run the function
        result = func()

        # Get the captured logs
        logs = log_capture.getvalue()

        return result, logs
    finally:
        # Clean up
        logger.removeHandler(handler)
        logger.setLevel(original_level)
        handler.close()


def test_python_script_natural_exit() -> None:
    """Test that a Python script exiting naturally shows 'exited on its own' message."""
    # Create a simple Python script that exits naturally
    script_content = dedent("""
        import sys
        print("Hello from Python!")
        sys.exit(0)
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:

        def run_test() -> str:
            cmd = f"{sys.executable} {script_path}"
            proc = run(cmd, rows=10, cols=40)

            # Wait for the script to finish naturally
            proc.subprocess_controller.wait()
            proc.exit()

            return "test completed"

        _, logs = capture_debug_logs(run_test)

        # Check that the logs contain the "exited on its own" message
        assert "has exited on its own" in logs, f"Expected 'exited on its own' in logs: {logs}"
        # Check that it does NOT contain the "after termination signal" message
        assert "after termination signal" not in logs, f"Unexpected 'after termination signal' in logs: {logs}"
    finally:
        import os

        os.unlink(script_path)


def test_python_script_context_manager_forced_exit() -> None:
    """Test that context manager termination shows 'exited after termination signal' message."""
    # Create a Python script that runs indefinitely (until terminated)
    script_content = dedent("""
        import time
        import signal

        print("Python script started, running indefinitely...")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Received interrupt, exiting...")
            exit(0)
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:

        def run_test() -> str:
            cmd = f"{sys.executable} {script_path}"
            with ht_process(cmd, rows=10, cols=40) as _:
                # Give the script time to start
                import time

                time.sleep(0.2)
                # Context manager will terminate subprocess on exit

            return "test completed"

        _, logs = capture_debug_logs(run_test)

        # Check that the logs contain the "after termination signal" message
        assert "after termination signal" in logs, f"Expected 'after termination signal' in logs: {logs}"
        # Check that it does NOT contain the "exited on its own" message
        assert "exited on its own" not in logs, f"Unexpected 'exited on its own' in logs: {logs}"
    finally:
        import os

        os.unlink(script_path)


def test_python_script_sigterm_responsive() -> None:
    """Test that explicitly calling terminate() on a SIGTERM-responsive script shows correct message."""
    # Create a Python script that responds to SIGTERM gracefully
    script_content = dedent("""
        import signal
        import time
        import sys

        def signal_handler(signum, frame):
            print(f"Received signal {signum}, exiting gracefully...")
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)

        print("Python script started, waiting for signal...")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Received interrupt, exiting...")
            sys.exit(0)
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:

        def run_test() -> str:
            cmd = f"{sys.executable} {script_path}"
            proc = run(cmd, rows=10, cols=40)

            # Give the script time to start
            import time

            time.sleep(0.2)

            # Explicitly terminate the subprocess
            proc.subprocess_controller.terminate()
            proc.subprocess_controller.wait()
            proc.exit()

            return "test completed"

        _, logs = capture_debug_logs(run_test)

        # Should see both the SIGTERM message and the "after termination signal" message
        assert "Sending SIGTERM" in logs, f"Expected 'Sending SIGTERM' in logs: {logs}"
        assert "after termination signal" in logs, f"Expected 'after termination signal' in logs: {logs}"
        # Should NOT see "exited on its own"
        assert "exited on its own" not in logs, f"Unexpected 'exited on its own' in logs: {logs}"
    finally:
        import os

        os.unlink(script_path)


def test_python_script_sigterm_ignore_needs_sigkill() -> None:
    """Test that a script ignoring SIGTERM requires SIGKILL and shows correct messages."""
    # Create a Python script that ignores SIGTERM and requires SIGKILL
    script_content = dedent("""
        import signal
        import time
        import sys

        def ignore_signal(signum, frame):
            print(f"Ignoring signal {signum}, continuing...")

        # Ignore SIGTERM
        signal.signal(signal.SIGTERM, ignore_signal)

        print("Python script started, ignoring SIGTERM...")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Received interrupt, exiting...")
            sys.exit(0)
    """)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:

        def run_test() -> str:
            cmd = f"{sys.executable} {script_path}"
            proc = run(cmd, rows=10, cols=40)

            # Give the script time to start
            import time

            time.sleep(0.2)

            # Try terminate first (should be ignored)
            proc.subprocess_controller.terminate()
            time.sleep(0.5)  # Give it time to ignore the signal

            # Now force kill it
            proc.subprocess_controller.kill()
            proc.subprocess_controller.wait()
            proc.exit()

            return "test completed"

        _, logs = capture_debug_logs(run_test)

        # Should see both SIGTERM and SIGKILL messages
        assert "Sending SIGTERM" in logs, f"Expected 'Sending SIGTERM' in logs: {logs}"
        assert "Sending SIGKILL" in logs, f"Expected 'Sending SIGKILL' in logs: {logs}"
        assert "after termination signal" in logs, f"Expected 'after termination signal' in logs: {logs}"
        # Should NOT see "exited on its own"
        assert "exited on its own" not in logs, f"Unexpected 'exited on its own' in logs: {logs}"
    finally:
        import os

        os.unlink(script_path)


def test_natural_exit_shows_correct_message() -> None:
    """Test that a process finishing naturally shows the correct message."""

    def run_test() -> str:
        proc = run("echo hello", rows=5, cols=20)

        # Wait for the process to finish naturally
        proc.subprocess_controller.wait()
        proc.exit()

        return "test completed"

    _, logs = capture_debug_logs(run_test)

    # Should see "exited on its own" message
    assert "exited on its own" in logs, f"Expected 'exited on its own' in logs: {logs}"
    # Should NOT see "after termination signal"
    assert "after termination signal" not in logs, f"Unexpected 'after termination signal' in logs: {logs}"
    # Should NOT see any SIGTERM/SIGKILL messages
    assert "Sending SIGTERM" not in logs, f"Unexpected 'Sending SIGTERM' in logs: {logs}"
    assert "Sending SIGKILL" not in logs, f"Unexpected 'Sending SIGKILL' in logs: {logs}"
