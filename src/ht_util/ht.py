import subprocess
import json
from time import sleep
import time
import threading
import queue
import os
from typing import Optional, List, Union
from .keys import KeyInput, keys_to_strings

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
        self.proc = proc
        self.event_queue = event_queue
        self.command = command
        self.subprocess_pid = pid
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

    def send_keys(self, keys: Union[KeyInput, List[KeyInput]]) -> bool:
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
        return True

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

    def snapshot(self, timeout: float = 5.0) -> str:
        """
        Returns:
            The raw terminal output as a string
        """
        self.proc.stdin.write(json.dumps({"type": "takeSnapshot"}) + "\n")
        self.proc.stdin.flush()        
        sleep(0.1)
        
        # Process events until we find the snapshot, but don't discard other events
        while True:
            event = self.event_queue.get(block=True, timeout=0.5)
            
            if event["type"] == "snapshot":
                snapshot_text = event['data']['text']
                return snapshot_text
            elif event["type"] == "output":
                # Don't lose output events - store them properly
                self.output_events.append(event)
            # For other event types (resize, pid, etc.), we could handle them here too
            # For now, we'll just continue to avoid losing the snapshot event

def run(command: str, rows: Optional[int] = None, cols: Optional[int] = None, no_exit: bool = False) -> HTProcess:
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
    
    # Add the command to run
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
                process.subprocess_pid = event["data"]["pid"]
                break
        except queue.Empty:
            continue
    
    return process


