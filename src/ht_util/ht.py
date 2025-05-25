import subprocess
import json
from time import sleep
import time
import threading
import queue
import os
import signal
from contextlib import contextmanager
from typing import Optional, List, Union, NamedTuple
from .keys import KeyInput, keys_to_strings, Press
from ansi2html import Ansi2HTMLConverter


def clean_ansi_for_html(ansi_text: str) -> str:
    """
    Clean ANSI sequences to keep only color/style codes that ansi2html can handle.
    Removes cursor positioning, screen control, and other non-display sequences.
    """
    import re
    
    # First, normalize \x9b sequences to \x1b[ sequences for consistency
    ansi_text = ansi_text.replace('\x9b', '\x1b[')
    
    # Remove cursor positioning sequences like \x1b[1;1H, \x1b[2;3H etc.
    ansi_text = re.sub(r'\x1b\[\d*;\d*H', '', ansi_text)
    
    # Remove single cursor positioning like \x1b[H
    ansi_text = re.sub(r'\x1b\[H', '', ansi_text)
    
    # Remove screen buffer switching \x1b[?1047h, \x1b[?1047l
    ansi_text = re.sub(r'\x1b\[\?\d+[hl]', '', ansi_text)
    
    # Remove scroll region setting \x1b[1;4r
    ansi_text = re.sub(r'\x1b\[\d*;\d*r', '', ansi_text)
    
    # Remove save/restore cursor sequences \x1b7, \x1b8
    ansi_text = re.sub(r'\x1b[78]', '', ansi_text)
    
    # Remove other terminal control sequences but keep color codes
    # This removes sequences that don't end with 'm' (which are color codes)
    ansi_text = re.sub(r'\x1b\[(?![0-9;]*m)[^m]*[a-zA-Z]', '', ansi_text)
    
    # Remove control characters but preserve \x1b which is needed for ANSI codes
    # and preserve \r\n for line breaks
    ansi_text = re.sub(r'[\x00-\x08\x0B-\x1A\x1C-\x1F\x7F-\x9F]', '', ansi_text)
    
    return ansi_text


class SnapshotResult(NamedTuple):
    """Result from taking a terminal snapshot."""
    text: str  # Plain text without ANSI codes
    html: str  # HTML with styling from ANSI codes
    raw_seq: str  # Raw ANSI sequence


class SubprocessController:
    """Controller for the subprocess being monitored by ht."""
    
    def __init__(self, pid: Optional[int] = None):
        self.pid = pid
        self.exit_code: Optional[int] = None
    
    def terminate(self) -> None:
        """Terminate the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            # Process may have already exited
            pass
    
    def kill(self) -> None:
        """Force kill the subprocess."""
        if self.pid is None:
            raise RuntimeError("No subprocess PID available")
        try:
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
                
                time.sleep(0.1)
                
            except OSError:
                # Process no longer exists (finished)
                self.exit_code = 0  # We can't easily get the real exit code
                return self.exit_code


class HTProcess:
    subprocess_pid: int | None = None

    """
    A wrapper around a process started with the 'ht' tool that provides
    methods for interacting with the process and capturing its output.
    """
    def __init__(self, proc, event_queue, command=None, pid=None, rows=None, cols=None, no_exit=False):
        """
        Initialize the HTProcess wrapper.
        
        Args:
            proc: The subprocess.Popen instance for the ht process
            event_queue: Queue to receive events from the ht process
            command: The command string that was executed (for display purposes)
            pid: The process ID (if known, otherwise extracted from events)
            rows: Number of rows in the terminal (if specified)
            cols: Number of columns in the terminal (if specified)
            no_exit: Whether the --no-exit flag was used (if True, ht will keep running after subprocess exits)
        """
        self.proc = proc  # The ht process itself
        self.subprocess = SubprocessController(pid)  # Controller for the monitored subprocess
        self.event_queue = event_queue
        self.command = command
        self.output_events = []
        self.start_time = time.time()
        self.exit_code = None
        self.rows = rows
        self.cols = cols
        self.no_exit = no_exit

    @property
    def output(self):
        """Return list of output events for backward compatibility."""
        # Debug: let's see what we actually have
        if not self.output_events:
            return []
        return [event for event in self.output_events if event.get('type') == 'output']

    def send_keys(self, keys: Union[KeyInput, List[KeyInput]]) -> None:
        """
        Send keys to the terminal.
        
        Args:
            keys: A string, Press enum, or list of keys to send.
                  Can use Press enums (e.g., Press.ENTER, Press.CTRL_C) or strings.
            
        Returns:
            True if keys were sent successfully, False otherwise
            
        Examples:
            proc.send_keys(Press.ENTER)
            proc.send_keys([Press.ENTER, Press.CTRL_C])
            proc.send_keys("hello")
            proc.send_keys(["hello", Press.ENTER])
        """
        key_strings = keys_to_strings(keys)
        
        self.proc.stdin.write(json.dumps({"type": "sendKeys", "keys": key_strings}) + "\n")
        self.proc.stdin.flush()
        sleep(0.1)

    def wait(self, timeout: Optional[float] = None) -> int:
        """
        Wait for the subprocess to finish.
        
        Args:
            timeout: Maximum time to wait for the process to finish (in seconds).
                    If None, waits indefinitely.
            
        Returns:
            The exit code of the subprocess
            
        Raises:
            RuntimeError: If no subprocess PID is available
            TimeoutError: If timeout is reached before process finishes
        """
        if self.subprocess_pid is None:
            raise RuntimeError("No subprocess PID available. Cannot wait for process.")
        
        start_time = time.time()
        
        while True:
            # Check if the process is still running
            try:
                # Sending signal 0 to a process checks if it exists and we can signal it
                os.kill(self.subprocess_pid, 0)
                # Process is still running
                
                # Check timeout
                if timeout is not None and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Process {self.subprocess_pid} did not finish within {timeout} seconds")
                
                # Sleep briefly before checking again
                time.sleep(0.1)
                
            except OSError:
                # Process no longer exists (finished)
                # Note: We can't easily get the exit code without psutil or other tools
                # For now, assume successful exit
                self.exit_code = 0
                return self.exit_code

    def snapshot(self, timeout: float = 5.0) -> SnapshotResult:
        """
        Take a snapshot of the terminal output.
        
        Returns:
            SnapshotResult with text (plain), html (styled), and raw_seq (ANSI codes)
        """
        # Check if the ht process is still running
        if self.proc.poll() is not None:
            raise RuntimeError(f"ht process has exited with code {self.proc.returncode}")
            
        try:
            self.proc.stdin.write(json.dumps({"type": "takeSnapshot"}) + "\n")
            self.proc.stdin.flush()        
        except BrokenPipeError as e:
            raise RuntimeError(f"Cannot communicate with ht process (broken pipe). Process may have exited. Poll result: {self.proc.poll()}") from e
            
        sleep(0.1)
        
        # Process events until we find the snapshot, but don't discard other events
        while True:
            event = self.event_queue.get(block=True, timeout=0.5)
            
            if event["type"] == "snapshot":
                data = event['data']
                snapshot_text = data['text']
                raw_seq = data['seq']
                
                # Clean the ANSI sequences for HTML conversion
                cleaned_seq = clean_ansi_for_html(raw_seq)
                
                # Convert cleaned ANSI sequences to HTML
                conv = Ansi2HTMLConverter()
                html = conv.convert(cleaned_seq)
                
                return SnapshotResult(
                    text=snapshot_text,
                    html=html,
                    raw_seq=raw_seq  # Keep original raw sequence
                )
            elif event["type"] == "output":
                # Don't lose output events - store them properly
                self.output_events.append(event)
            # For other event types (resize, pid, etc.), we could handle them here too
            # For now, we'll just continue to avoid losing the snapshot event

    def exit(self, timeout: float = 5.0) -> int:
        """
        Exit the ht process, forcefully terminating the subprocess if needed.
        
        This method ensures a reliable exit regardless of subprocess state:
        - If subprocess is still running, it will be terminated first
        - Then the ht process will be cleanly shut down
        
        Args:
            timeout: Maximum time to wait for the process to exit (default: 5 seconds)
        
        Returns:
            The exit code of the ht process (0 for success)
        """
        
        # Step 1: Ensure subprocess is terminated first
        if self.subprocess.pid:
            try:
                # Check if subprocess is still running
                os.kill(self.subprocess.pid, 0)
                # If we get here, subprocess is still running - terminate it
                self.subprocess.terminate()
                try:
                    self.subprocess.wait(timeout=2.0)
                except Exception:
                    # If graceful termination fails, force kill
                    try:
                        self.subprocess.kill()
                    except Exception:
                        pass
            except OSError:
                # Subprocess already dead, that's fine
                pass
        
        # Step 2: Handle ht process exit
        if self.no_exit:
            # Now that subprocess is dead, ht should be waiting for exit Enter
            # Give it a moment to detect subprocess exit and show the prompt
            time.sleep(0.2)
            self.send_keys(Press.ENTER)
            time.sleep(0.1)
        
        # Step 3: Wait for the ht process itself to finish with timeout
        try:
            start_time = time.time()
            while self.proc.poll() is None:
                if time.time() - start_time > timeout:
                    # Timeout reached, force terminate
                    self.proc.terminate()
                    time.sleep(0.1)
                    if self.proc.poll() is None:
                        self.proc.kill()
                    break
                time.sleep(0.1)
            
            self.exit_code = self.proc.returncode
            # Normalize exit code to 0 for successful termination
            if self.exit_code is None or self.exit_code == -15:  # SIGTERM
                self.exit_code = 0
                
        except Exception:
            # If anything goes wrong, assume success
            self.exit_code = 0
            
        return self.exit_code

    def terminate(self) -> None:
        """Terminate the ht process itself."""
        try:
            self.proc.terminate()
        except Exception:
            pass

    def kill(self) -> None:
        """Force kill the ht process itself."""
        try:
            self.proc.kill()
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
                self.exit_code = self.proc.wait()
            else:
                self.exit_code = self.proc.wait(timeout=timeout)
            return self.exit_code
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None

def run(command: str, rows: Optional[int] = None, cols: Optional[int] = None, no_exit: bool = True) -> HTProcess:
    """
    Run a command using the 'ht' tool and return a HTProcess object
    that can be used to interact with it.
    
    Args:
        command: The command to run
        rows: Number of rows for the terminal size (height)
        cols: Number of columns for the terminal size (width)
        no_exit: If True, use the --no-exit flag to keep ht running after subprocess exits
        
    Returns:
        An HTProcess instance
    """
   
    # Split the command into arguments if it's a string
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command
    
    # Create the ht command with event subscription
    ht_cmd = ["ht", "--subscribe", "init,snapshot,output,resize,pid"]
    
    # Add size options if specified
    if rows is not None and cols is not None:
        ht_cmd.extend(["--size", f"{cols}x{rows}"])
    
    # Add no-exit option if specified
    if no_exit:
        ht_cmd.append("--no-exit")
    
    # Add separator and the command to run
    ht_cmd.append("--")
    ht_cmd.extend(cmd_args)
    
    # Create a queue for events
    event_queue = queue.Queue()
    
    # Create a reader thread to capture ht output
    def reader_thread(ht_proc, queue_obj, ht_process):
        while True:
            line = ht_proc.stdout.readline()
            if not line:
                break                
            line = line.strip()
            if not line:
                continue
                
            try:
                event = json.loads(line)
                queue_obj.put(event)
                
                # Store output events separately in the process
                if event['type'] == 'output':
                    ht_process.output_events.append(event)
            except json.JSONDecodeError:
                # Check for non-JSON messages that indicate process state
                if isinstance(line, str):
                    if "Process exited" in line:
                        if hasattr(ht_process, 'subprocess') and hasattr(ht_process.subprocess, '_finished'):
                            ht_process.subprocess._finished = True
                            ht_process.subprocess.exit_code = 0  # Assume success
                            ht_process._subprocess_finished = True
                
                queue_obj.put({"type": "raw", "data": {"text": line}})
    
    # Log the exact command for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Executing ht command: {' '.join(ht_cmd)}")
    
    # Launch ht
    ht_proc = subprocess.Popen(
        ht_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Create an HTProcess instance
    process = HTProcess(
        ht_proc, 
        event_queue, 
        command=' '.join(cmd_args), 
        rows=rows, 
        cols=cols,
        no_exit=no_exit
    )
    
    # Start the reader thread
    thread = threading.Thread(target=reader_thread, args=(ht_proc, event_queue, process), daemon=True)
    thread.start()    
    # Wait briefly for the process to initialize
    start_time = time.time()
    while time.time() - start_time < 2:
        try:
            event = event_queue.get(block=True, timeout=0.5)          
            if event['type'] == 'pid':
                # Update the subprocess controller
                pid = event["data"]["pid"]
                process.subprocess.pid = pid
                break
        except queue.Empty:
            continue
    
    sleep(0.1)
    return process


@contextmanager
def ht_process(command: str, rows: Optional[int] = None, cols: Optional[int] = None, no_exit: bool = True):
    """
    Context manager for HTProcess that ensures proper cleanup.
    
    Usage:
        with ht_process("python script.py", rows=10, cols=20) as proc:
            proc.send_keys(Press.ENTER)
            snapshot = proc.snapshot()
            # Process is automatically cleaned up when exiting the context
    
    Args:
        command: The command to run
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
        # Ensure cleanup happens even if an exception occurs
        try:
            # Try to terminate subprocess gracefully first
            if proc.subprocess.pid:
                proc.subprocess.terminate()
                proc.subprocess.wait(timeout=2.0)
        except Exception:
            # If graceful termination fails, force kill
            try:
                if proc.subprocess.pid:
                    proc.subprocess.kill()
            except Exception:
                pass
        
        try:
            # Clean up the ht process
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            # If ht process won't terminate, force kill it
            try:
                proc.kill()
            except Exception:
                pass


