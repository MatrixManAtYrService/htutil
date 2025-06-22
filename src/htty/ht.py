import json
import logging
import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from time import sleep
from typing import Any, Dict, Iterator, List, Optional, Union

from ansi2html import Ansi2HTMLConverter

from .keys import KeyInput, Press, keys_to_strings

# Constants
DEFAULT_SLEEP_AFTER_KEYS = 0.1
DEFAULT_SUBPROCESS_WAIT_TIMEOUT = 2.0
DEFAULT_SNAPSHOT_TIMEOUT = 5.0
DEFAULT_EXIT_TIMEOUT = 5.0
DEFAULT_GRACEFUL_TERMINATION_TIMEOUT = 5.0
SNAPSHOT_RETRY_TIMEOUT = 0.5
SUBPROCESS_EXIT_DETECTION_DELAY = 0.2
MAX_SNAPSHOT_RETRIES = 10


@dataclass
class HTBinary:
    """Represents an ht binary with helper methods for common operations."""

    path: str
    _cleanup_context: Optional[object] = None

    def build_command(self, *args: str) -> List[str]:
        """Build a command list starting with the ht binary path."""
        return [self.path] + list(args)

    def run_subprocess(self, *args: str, **kwargs: Any) -> subprocess.Popen[str]:
        """Run ht as a subprocess with the given arguments."""
        cmd = self.build_command(*args)
        return subprocess.Popen(cmd, **kwargs)


def _try_user_specified_binary() -> Optional[str]:
    """Try to use user-specified ht binary from HTTY_HT_BIN environment variable."""
    user_ht = os.environ.get("HTTY_HT_BIN")
    if not user_ht or not user_ht.strip():
        return None

    user_ht_path = Path(user_ht)
    if user_ht_path.is_file() and os.access(str(user_ht_path), os.X_OK):
        logger = logging.getLogger(__name__)
        logger.info("Using user-specified ht binary from HTTY_HT_BIN")
        return str(user_ht_path)
    else:
        raise RuntimeError(
            f"HTTY_HT_BIN='{user_ht}' is not a valid executable file. "
            f"Please check that the path exists and is executable."
        )


def _try_bundled_binary() -> Optional[str]:
    """Try to use bundled ht binary."""
    try:
        from importlib import resources as impresources

        from . import _bundled

        bundled_files = impresources.files(_bundled)
        ht_resource = bundled_files / "ht"

        if ht_resource.is_file():
            logger = logging.getLogger(__name__)
            logger.info("Using bundled ht binary")
            with impresources.as_file(ht_resource) as ht_path:
                os.chmod(str(ht_path), 0o755)
                return str(ht_path)
        else:
            return None

    except (ImportError, FileNotFoundError, AttributeError):
        logger = logging.getLogger(__name__)
        logger.debug("No bundled ht binary found, falling back to system PATH")
        return None


def _try_system_binary() -> Optional[str]:
    """Try to use system ht binary from PATH."""
    system_ht = shutil.which("ht")
    if system_ht:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Using system ht binary from PATH: {system_ht}. "
            "Expect trouble if this ht does not have the changes in this fork: "
            "https://github.com/MatrixManAtYrService/ht. "
            "Consider using a wheel distribution of htty, which bundles the forked ht."
        )
        return system_ht
    return None


@contextmanager
def ht_binary() -> Iterator[HTBinary]:
    """
    Context manager that provides access to the ht binary.

    Order of precedence:
    1. HTTY_HT_BIN environment variable (if set and valid) - user override
    2. Bundled ht binary via importlib.resources (production/wheel)
    3. System 'ht' command from PATH (development fallback)

    Usage:
        with ht_binary() as ht:
            cmd = ht.build_command("--help")
            ht_proc = ht.run_subprocess("--version")

    Raises:
        RuntimeError: If ht binary cannot be found anywhere
    """

    # Try each strategy in order
    for strategy in [_try_user_specified_binary, _try_bundled_binary, _try_system_binary]:
        try:
            ht_path = strategy()
            if ht_path:
                yield HTBinary(ht_path)
                return
        except RuntimeError:
            # Re-raise user configuration errors immediately
            raise

    # If we get here, ht is not available anywhere
    import platform

    arch = platform.machine()
    system = platform.system()

    raise RuntimeError(
        f"Could not find ht binary for {system} {arch}.\n\n"
        "This likely happened because:\n"
        "• You installed from source (no bundled ht binary)\n"
        "• No pre-built wheel available for your architecture\n\n"
        "Solutions:\n"
        "1. Install ht separately: https://github.com/andyk/ht\n"
        "   Then ensure it's in your PATH\n"
        "2. Set HTTY_HT_BIN to point to ht binary:\n"
        "   export HTTY_HT_BIN=/path/to/ht\n"
        "3. Use a supported architecture with pre-built wheels:\n"
        "   • Linux: x86_64, aarch64\n"
        "   • macOS: x86_64, arm64\n\n"
        "For help: https://github.com/MatrixManAtYrService/htty/issues"
    )


def clean_ansi_for_html(ansi_text: str) -> str:
    """
    Clean ANSI sequences to keep only color/style codes that ansi2html can handle.

    This function removes:
    - Cursor positioning sequences (\x1b[1;1H, \x1b[2;3H, etc.)
    - Screen buffer switching (\x1b[?1047h, \x1b[?1047l)
    - Scroll region settings (\x1b[1;4r)
    - Save/restore cursor sequences (\x1b7, \x1b8)
    - Other terminal control sequences that don't end with 'm' (color codes)
    - Most control characters except ANSI escape sequences and line breaks
    """
    import re

    # Normalize \x9b sequences to \x1b[ sequences for consistency
    ansi_text = ansi_text.replace("\x9b", "\x1b[")

    # Remove cursor positioning sequences like \x1b[1;1H, \x1b[2;3H etc.
    ansi_text = re.sub(r"\x1b\[\d*;\d*H", "", ansi_text)

    # Remove single cursor positioning like \x1b[H
    ansi_text = re.sub(r"\x1b\[H", "", ansi_text)

    # Remove screen buffer switching \x1b[?1047h, \x1b[?1047l
    ansi_text = re.sub(r"\x1b\[\?\d+[hl]", "", ansi_text)

    # Remove scroll region setting \x1b[1;4r
    ansi_text = re.sub(r"\x1b\[\d*;\d*r", "", ansi_text)

    # Remove save/restore cursor sequences \x1b7, \x1b8
    ansi_text = re.sub(r"\x1b[78]", "", ansi_text)

    # Remove other terminal control sequences but keep color codes
    # This removes sequences that don't end with 'm' (which are color codes)
    ansi_text = re.sub(r"\x1b\[(?![0-9;]*m)[^m]*[a-zA-Z]", "", ansi_text)

    # Remove control characters but preserve \x1b which is needed for ANSI codes
    # and preserve \r\n for line breaks
    ansi_text = re.sub(r"[\x00-\x08\x0B-\x1A\x1C-\x1F\x7F-\x9F]", "", ansi_text)

    return ansi_text


@dataclass
class SnapshotResult:
    """Result from taking a terminal snapshot."""

    text: str  # Plain text without ANSI codes
    html: str  # HTML with styling from ANSI codes
    raw_seq: str  # Raw ANSI sequence


class SubprocessController:
    """Controller for the subprocess being monitored by ht."""

    def __init__(self, pid: Optional[int] = None):
        self.pid = pid
        self.exit_code: Optional[int] = None
        self._termination_initiated = False  # Track if we initiated termination

    def poll(self) -> Optional[int]:
        """Check if the subprocess is still running."""
        if self.pid is None:
            return self.exit_code
        try:
            os.kill(self.pid, 0)
            return None  # Process is still running
        except OSError:
            return self.exit_code  # Process has exited

    def terminate(self) -> None:
        """Terminate the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f"Sending SIGTERM to process {self.pid}")
            self._termination_initiated = True
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            # Process may have already exited
            pass

    def kill(self) -> None:
        """Force kill the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f"Sending SIGKILL to process {self.pid}")
            self._termination_initiated = True
            os.kill(self.pid, signal.SIGKILL)
        except OSError:
            # Process may have already exited
            pass

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """
        Wait for the subprocess to finish.

        Args:
            timeout: Maximum time to wait (in seconds). If None, waits indefinitely.

        Returns:
            The exit code of the subprocess, or None if timeout reached
        """
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")

        start_time = time.time()
        while True:
            try:
                # Check if the subprocess is still running
                os.kill(self.pid, 0)
                # Process is still running

                # Check timeout
                if timeout is not None and (time.time() - start_time) > timeout:
                    return None  # Timeout reached

                time.sleep(DEFAULT_SLEEP_AFTER_KEYS)
            except OSError:
                # Process has exited
                logger = logging.getLogger(__name__)

                # Try to get the actual exit code using waitpid
                try:
                    pid_result, status = os.waitpid(self.pid, os.WNOHANG)
                    if pid_result == self.pid and status != 0:
                        # We got actual status information
                        if os.WIFEXITED(status):
                            self.exit_code = os.WEXITSTATUS(status)
                            if self._termination_initiated:
                                logger.debug(
                                    f"Process {self.pid} has exited after termination signal with code {self.exit_code}"
                                )
                            else:
                                logger.debug(f"Process {self.pid} has exited on its own with code {self.exit_code}")
                        elif os.WIFSIGNALED(status):
                            signal_num = os.WTERMSIG(status)
                            self.exit_code = 128 + signal_num  # Standard convention
                            logger.debug(
                                f"Process {self.pid} terminated by signal {signal_num}, exit code {self.exit_code}"
                            )
                        else:
                            # Unexpected status
                            self.exit_code = 1
                            logger.debug(f"Process {self.pid} exited with unexpected status {status}")
                    else:
                        # Process was already reaped or no status available
                        # This is common when the parent process (ht) has already collected the child
                        if self.exit_code is None:
                            logger.warning(
                                f"Could not determine exit code for process {self.pid} - process was already reaped"
                            )
                            raise RuntimeError(f"Unable to determine exit code for process {self.pid}")

                        if self._termination_initiated:
                            logger.debug(
                                f"Process {self.pid} has exited after termination signal with code {self.exit_code}"
                            )
                        else:
                            logger.debug(f"Process {self.pid} has exited on its own with code {self.exit_code}")

                except OSError:
                    # Couldn't call waitpid, but we know the process exited
                    if self.exit_code is None:
                        if self._termination_initiated:
                            # We terminated the process but can't get the exact exit code
                            # Use conventional exit code for SIGKILL (128 + 9 = 137)
                            self.exit_code = 137
                            logger.warning(
                                f"Could not determine exit code for process {self.pid} after termination - "
                                f"waitpid failed, assuming exit code {self.exit_code}"
                            )
                        else:
                            # Process exited on its own but we can't determine exit code
                            logger.warning(f"Could not determine exit code for process {self.pid} - waitpid failed")
                            raise RuntimeError(f"Unable to determine exit code for process {self.pid}")

                    if self._termination_initiated:
                        logger.debug(
                            f"Process {self.pid} has exited after termination signal with code {self.exit_code}"
                        )
                    else:
                        logger.debug(f"Process {self.pid} has exited on its own with code {self.exit_code}")

                return self.exit_code


class HTProcess:
    """
    A wrapper around a process started with the 'ht' tool that provides
    methods for interacting with the process and capturing its output.
    """

    def __init__(
        self,
        ht_proc: subprocess.Popen[str],
        event_queue: Queue[Dict[str, Any]],
        command: Optional[str] = None,
        pid: Optional[int] = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        no_exit: bool = False,
    ) -> None:
        """
        Initialize the HTProcess wrapper.

        Args:
            ht_proc: The subprocess.Popen instance for the ht process
            event_queue: Queue to receive events from the ht process
            command: The command string that was executed (for display purposes)
            pid: The process ID (if known, otherwise extracted from events)
            rows: Number of rows in the terminal (if specified)
            cols: Number of columns in the terminal (if specified)
            no_exit: Whether the --no-exit flag was used (if True, ht will keep running after subprocess exits)
        """
        self.ht_proc = ht_proc
        self.subprocess_controller = SubprocessController(pid)
        self.event_queue = event_queue
        self.command = command
        self.output_events: List[Dict[str, Any]] = []
        self.unknown_events: List[Dict[str, Any]] = []
        self.latest_snapshot: Optional[str] = None
        self.start_time = time.time()
        self.exit_code: Optional[int] = None
        self.rows = rows
        self.cols = cols
        self.no_exit = no_exit
        self.subprocess_exited = False
        self.output: List[str] = []

    def get_output(self) -> List[Dict[str, Any]]:
        """Return list of output events for backward compatibility."""
        if not self.output_events:
            return []
        return [event for event in self.output_events if event.get("type") == "output"]

    def send_keys(self, keys: Union[KeyInput, List[KeyInput]]) -> None:
        """
        Send keys to the terminal.

        Args:
            keys: A string, Press enum, or list of keys to send.
                  Can use Press enums (e.g., Press.ENTER, Press.CTRL_C) or strings.

        Note:
            This method does not return a success/failure status.

        Examples:
            proc.send_keys(Press.ENTER)
            proc.send_keys([Press.ENTER, Press.CTRL_C])
            proc.send_keys("hello")
            proc.send_keys(["hello", Press.ENTER])
        """
        key_strings = keys_to_strings(keys)

        if self.ht_proc.stdin is not None:
            self.ht_proc.stdin.write(json.dumps({"type": "sendKeys", "keys": key_strings}) + "\n")
            self.ht_proc.stdin.flush()
        sleep(DEFAULT_SLEEP_AFTER_KEYS)

    def snapshot(self, timeout: float = DEFAULT_SNAPSHOT_TIMEOUT) -> SnapshotResult:
        """
        Take a snapshot of the terminal output.

        Returns:
            SnapshotResult with text (plain), html (styled), and raw_seq (ANSI codes)
        """
        if self.ht_proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self.ht_proc.returncode}")

        try:
            if self.ht_proc.stdin is not None:
                self.ht_proc.stdin.write(json.dumps({"type": "takeSnapshot"}) + "\n")
                self.ht_proc.stdin.flush()
            else:
                raise RuntimeError("ht process stdin is not available")
        except BrokenPipeError as e:
            raise RuntimeError(
                f"Cannot communicate with ht process (broken pipe). "
                f"Process may have exited. Poll result: {self.ht_proc.poll()}"
            ) from e

        sleep(DEFAULT_SLEEP_AFTER_KEYS)

        # Process events until we find the snapshot
        retry_count = 0
        while retry_count < MAX_SNAPSHOT_RETRIES:
            try:
                event = self.event_queue.get(block=True, timeout=SNAPSHOT_RETRY_TIMEOUT)
            except queue.Empty:
                retry_count += 1
                continue

            if event["type"] == "snapshot":
                data = event["data"]
                snapshot_text = data["text"]
                raw_seq = data["seq"]

                cleaned_seq = clean_ansi_for_html(raw_seq)

                ansi_converter = Ansi2HTMLConverter()
                html = ansi_converter.convert(cleaned_seq)

                return SnapshotResult(
                    text=snapshot_text,
                    html=html,
                    raw_seq=raw_seq,
                )
            elif event["type"] == "output":
                self.output_events.append(event)
            elif event["type"] == "pid":
                if self.subprocess_controller.pid is None:
                    self.subprocess_controller.pid = event["data"]["pid"]
            elif event["type"] == "exitCode":
                self.subprocess_exited = True
                self.subprocess_controller.exit_code = event.get("data", {}).get("exitCode")
            elif event["type"] == "resize":
                if "data" in event:
                    data = event["data"]
                    if "rows" in data:
                        self.rows = data["rows"]
                    if "cols" in data:
                        self.cols = data["cols"]
            elif event["type"] == "init":
                pass
            else:
                self.unknown_events.append(event)

        raise RuntimeError(
            f"Failed to receive snapshot event after {MAX_SNAPSHOT_RETRIES} attempts. "
            f"ht process may have exited or stopped responding."
        )

    def exit(self, timeout: float = DEFAULT_EXIT_TIMEOUT) -> int:
        """
        Exit the ht process, forcefully terminating the subprocess if needed.

        This method ensures a reliable exit regardless of subprocess state:
        - If subprocess is still running, it will be terminated first
        - Then the ht process will be cleanly shut down

        Args:
            timeout: Maximum time to wait for the process to exit (default: 5 seconds)

        Returns:
            The exit code of the ht process

        Raises:
            RuntimeError: If unable to determine exit code or process cleanup fails
        """

        # Step 1: Ensure subprocess is terminated first
        if self.subprocess_controller.pid:
            try:
                os.kill(self.subprocess_controller.pid, 0)
                self.subprocess_controller.terminate()
                try:
                    self.subprocess_controller.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Graceful subprocess termination failed: {e}")
                    try:
                        self.subprocess_controller.kill()
                    except Exception as kill_error:
                        logger.error(f"Force kill of subprocess failed: {kill_error}")
                        raise RuntimeError("Failed to terminate subprocess") from kill_error
            except OSError:
                pass

        # Step 2: Handle ht process exit
        if self.no_exit:
            time.sleep(SUBPROCESS_EXIT_DETECTION_DELAY)
            self.send_keys(Press.ENTER)
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        # Step 3: Wait for the ht process itself to finish with timeout
        start_time = time.time()
        while self.ht_proc.poll() is None:
            if time.time() - start_time > timeout:
                # Timeout reached, force terminate
                logger = logging.getLogger(__name__)
                logger.warning(f"ht process did not exit within {timeout}s, terminating")
                self.ht_proc.terminate()
                try:
                    self.ht_proc.wait(timeout=DEFAULT_GRACEFUL_TERMINATION_TIMEOUT)
                except subprocess.TimeoutExpired:
                    logger.error(
                        f"ht process did not respond to SIGTERM within "
                        f"{DEFAULT_GRACEFUL_TERMINATION_TIMEOUT}s, force killing"
                    )
                    self.ht_proc.kill()
                    self.ht_proc.wait()  # Wait for kill to complete
                break
            time.sleep(DEFAULT_SLEEP_AFTER_KEYS)

        self.exit_code = self.ht_proc.returncode
        if self.exit_code is None:
            raise RuntimeError("Failed to determine ht process exit code")

        return self.exit_code

    def terminate(self) -> None:
        """Terminate the ht process itself."""
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f"Terminating ht process {self.ht_proc.pid}")
            self.ht_proc.terminate()
        except Exception:
            pass

    def kill(self) -> None:
        """Force kill the ht process itself."""
        try:
            logger = logging.getLogger(__name__)
            logger.debug(f"Force killing ht process {self.ht_proc.pid}")
            self.ht_proc.kill()
        except Exception:
            pass

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        """
        Wait for the ht process itself to finish.

        Args:
            timeout: Maximum time to wait (in seconds). If None, waits indefinitely.

        Returns:
            The exit code of the ht process, or None if timeout reached
        """
        try:
            if timeout is None:
                self.exit_code = self.ht_proc.wait()
            else:
                self.exit_code = self.ht_proc.wait(timeout=timeout)
            return self.exit_code
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None


def run(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
) -> HTProcess:
    """
    Run a command using the 'ht' tool and return a HTProcess object
    that can be used to interact with it.

    Args:
        command: The command to run (string or list of strings)
        rows: Number of rows for the terminal size (height)
        cols: Number of columns for the terminal size (width)
        no_exit: If True, use the --no-exit flag to keep ht running after subprocess exits

    Returns:
        An HTProcess instance
    """

    # Handle both string commands and pre-split argument lists
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command

    # Create a queue for events
    event_queue: Queue[Dict[str, Any]] = queue.Queue()

    # Use the ht binary context manager to start the process
    with ht_binary() as ht:
        # Build the ht command with event subscription
        ht_cmd_args = [
            "--subscribe",
            "init,snapshot,output,resize,pid,exitCode",
        ]

        # Add size options if specified
        if rows is not None and cols is not None:
            ht_cmd_args.extend(["--size", f"{cols}x{rows}"])

        # Add no-exit option if specified
        if no_exit:
            ht_cmd_args.append("--no-exit")

        # Add separator and the command to run
        ht_cmd_args.append("--")
        ht_cmd_args.extend(cmd_args)

        # Log the exact command for debugging
        full_cmd = ht.build_command(*ht_cmd_args)
        logger = logging.getLogger(__name__)
        logger.debug(f"Executing ht command: {' '.join(full_cmd)}")

        # Launch ht using the HTBinary helper
        ht_proc = ht.run_subprocess(
            *ht_cmd_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    # Create a reader thread to capture ht output
    def reader_thread(
        ht_proc: subprocess.Popen[str],
        queue_obj: Queue[Dict[str, Any]],
        ht_process: HTProcess,
    ) -> None:
        while True:
            if ht_proc.stdout is None:
                break
            line = ht_proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                queue_obj.put(event)

                if event["type"] == "output":
                    ht_process.output_events.append(event)
                elif event["type"] == "exitCode":
                    ht_process.subprocess_exited = True
                    if hasattr(ht_process, "subprocess_controller"):
                        exit_code = event.get("data", {}).get("exitCode")
                        if exit_code is not None:
                            ht_process.subprocess_controller.exit_code = exit_code
                        else:
                            logger = logging.getLogger(__name__)
                            logger.error(f"Received exitCode event without valid exit code data: {event}")
            except json.JSONDecodeError as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Received non-JSON output from ht process: {line!r}")
                raise RuntimeError(f"ht process produced unexpected non-JSON output: {line!r}") from e

    # Create an HTProcess instance
    process = HTProcess(
        ht_proc,
        event_queue,
        command=" ".join(cmd_args),
        rows=rows,
        cols=cols,
        no_exit=no_exit,
    )

    # Start the reader thread
    thread = threading.Thread(target=reader_thread, args=(ht_proc, event_queue, process), daemon=True)
    thread.start()
    # Wait briefly for the process to initialize
    start_time = time.time()
    while time.time() - start_time < 2:
        try:
            event = event_queue.get(block=True, timeout=0.5)
            if event["type"] == "pid":
                pid = event["data"]["pid"]
                process.subprocess_controller.pid = pid
                break
        except queue.Empty:
            continue

    sleep(DEFAULT_SLEEP_AFTER_KEYS)
    return process


@contextmanager
def ht_process(
    command: Union[str, List[str]],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    no_exit: bool = True,
):
    """
    Context manager for HTProcess that ensures proper cleanup.

    Usage:
        with ht_process("python script.py", rows=10, cols=20) as proc:
            proc.send_keys(Press.ENTER)
            snapshot = proc.snapshot()
            # Process is automatically cleaned up when exiting the context

    Args:
        command: The command to run (string or list of strings)
        rows: Number of rows for the terminal size
        cols: Number of columns for the terminal size
        no_exit: Whether to use --no-exit flag (default: True)

    Yields:
        HTProcess instance with automatic cleanup
    """
    proc = run(command, rows=rows, cols=cols, no_exit=no_exit)
    try:
        yield proc
    finally:
        try:
            if proc.subprocess_controller.pid:
                proc.subprocess_controller.terminate()
                proc.subprocess_controller.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to gracefully terminate subprocess: {e}")
            try:
                if proc.subprocess_controller.pid:
                    proc.subprocess_controller.kill()
            except Exception as kill_error:
                logger.error(f"Failed to force kill subprocess: {kill_error}")

        try:
            proc.terminate()
            proc.wait(timeout=DEFAULT_SUBPROCESS_WAIT_TIMEOUT)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to gracefully terminate ht process: {e}")
            try:
                proc.kill()
            except Exception as kill_error:
                logger.error(f"Failed to force kill ht process: {kill_error}")


def main() -> None:
    """
    Command-line entry point for the 'ht' command.

    This function provides direct access to the bundled ht binary,
    passing through all command-line arguments unchanged.
    """
    import sys

    try:
        with ht_binary() as ht:
            # Get all command-line arguments except the script name
            args = sys.argv[1:]

            # Build and execute the ht command
            cmd = ht.build_command(*args)

            # Use os.execvp to replace the current process with ht
            # This ensures that signals, exit codes, and I/O work exactly as expected
            import os

            os.execvp(cmd[0], cmd)

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
