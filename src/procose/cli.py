"""
Procose CLI for displaying subprocess output in a structured format.

This module provides a command-line interface that runs subprocesses
and displays their output with separate sections for stdout and stderr.
"""

import sys
import time
import subprocess
import datetime
import threading
import signal
import os
import queue
from typing import List, Dict, Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.box import Box, SIMPLE
from rich.layout import Layout


def format_duration(seconds):
    """Format seconds into a human-readable duration."""
    minutes, seconds = divmod(int(seconds), 60)
    if minutes > 0:
        return f"{minutes}:{seconds:02d}"
    return f"0:{seconds:02d}"


class VerticalLayout:
    """A simple container to display multiple renderables vertically."""
    
    def __init__(self, *renderables):
        self.renderables = renderables
    
    def __rich_console__(self, console, options):
        for renderable in self.renderables:
            yield renderable


def run_command_with_display(command):
    """Run a command and display its output in structured format."""
    # Create a rich console
    console = Console()
    
    # Initialize storage for output
    stdout_lines = []
    stderr_lines = []
    exit_code = None
    
    # Record start time
    start_time = datetime.datetime.now()
    
    # Create a queue for thread-safe communication
    update_queue = queue.Queue()
    
    # Flag to indicate the process has completed
    process_completed = threading.Event()
    display_completed = threading.Event()
    
    # Function to generate the display
    def generate_display(final=False):
        # Calculate elapsed time
        elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
        
        # Format command name
        cmd_str = " ".join(command)
        if len(cmd_str) > 30:
            cmd_str = cmd_str[:27] + "..."
        
        # Header text
        header = Text()
        header.append(f"{start_time.strftime('%H:%M:%S')}", style="bold")
        header.append(" • ")
        header.append(f"{cmd_str}", style="bold blue")
        header.append(" • ")
        header.append(f"pid: {process.pid if 'process' in locals() else 'N/A'}")
        
        # Format stdout
        stdout_text = Text("stdout: ")
        if stdout_lines:
            stdout_text.append(stdout_lines[0])
            for line in stdout_lines[1:]:
                stdout_text.append("\n        ")
                stdout_text.append(line)
        else:
            stdout_text.append("(no output)")
        
        # Format stderr (only if there's content or it's the final display)
        stderr_text = Text("stderr: ", style="red")
        if stderr_lines:
            stderr_text.append(stderr_lines[0])
            for line in stderr_lines[1:]:
                stderr_text.append("\n        ")
                stderr_text.append(line)
        else:
            stderr_text.append("(no output)")
        
        # Status line (at the bottom)
        status = Text()
        if exit_code is None:
            status.append("running", style="yellow bold")
        else:
            status.append("finished", style="green bold")
        
        status.append(" • ")
        status.append(f"duration: {format_duration(elapsed_time)}")
        
        if exit_code is not None:
            status.append(" • ")
            style = "green" if exit_code == 0 else "red"
            status.append(f"code: {exit_code}", style=style)
        
        # Combine elements
        renderables = [header, stdout_text]
        
        # Only include stderr if it has content or it's the final display
        if stderr_lines or final:
            renderables.append(stderr_text)
        
        # Add status at the bottom
        renderables.append(status)
        
        return VerticalLayout(*renderables)
    
    # Function to read from a stream and store the output
    def read_stream(stream, lines, stream_name):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    # Add the line to the output
                    lines.append(line.rstrip())
                    # Signal that an update is needed
                    update_queue.put("update")
        except Exception as e:
            # Signal that an error occurred
            update_queue.put(f"error: {str(e)}")
        
        # Signal that this stream is done
        update_queue.put(f"{stream_name}_done")
    
    # Start the live display with a placeholder
    with Live(Text("Starting process..."), refresh_per_second=4, console=console, auto_refresh=False) as live:
        try:
            # Start the subprocess
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Initial display update
            live.update(generate_display())
            
            # Create threads to read stdout and stderr
            stdout_thread = threading.Thread(
                target=read_stream, 
                args=(process.stdout, stdout_lines, "stdout"),
                daemon=True
            )
            
            stderr_thread = threading.Thread(
                target=read_stream, 
                args=(process.stderr, stderr_lines, "stderr"),
                daemon=True
            )
            
            # Start the threads
            stdout_thread.start()
            stderr_thread.start()
            
            # Monitor thread for timing updates
            def update_timer():
                last_update = time.time()
                while not process_completed.is_set():
                    current_time = time.time()
                    if current_time - last_update >= 0.5:
                        update_queue.put("timer")
                        last_update = current_time
                    time.sleep(0.1)
            
            timer_thread = threading.Thread(target=update_timer, daemon=True)
            timer_thread.start()
            
            # Create a thread to monitor the process
            def monitor_process():
                # Wait for the process to complete
                exit_nonlocal = process.wait()
                
                # Mark the process as completed
                process_completed.set()
                
                # Signal that the process is done
                update_queue.put(f"process_done:{exit_nonlocal}")
            
            process_thread = threading.Thread(target=monitor_process, daemon=True)
            process_thread.start()
            
            # Variables to track thread completion
            stdout_done = False
            stderr_done = False
            process_done = False
            
            # Main loop to process updates
            while not (stdout_done and stderr_done and process_done):
                try:
                    # Wait for an update with timeout
                    try:
                        message = update_queue.get(timeout=0.5)
                    except queue.Empty:
                        # Periodic update even if no new output
                        live.update(generate_display())
                        continue
                    
                    # Process the message
                    if message == "update" or message == "timer":
                        # Update the display
                        live.update(generate_display())
                        live.refresh()  # Explicitly refresh
                    
                    elif message == "stdout_done":
                        stdout_done = True
                    
                    elif message == "stderr_done":
                        stderr_done = True
                    
                    elif message.startswith("process_done:"):
                        process_done = True
                        exit_code = int(message.split(":", 1)[1])
                    
                    elif message.startswith("error:"):
                        # Handle error (could log it)
                        pass
                    
                    # Mark the message as processed
                    update_queue.task_done()
                    
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    if not process_completed.is_set():
                        process.terminate()
                        exit_code = 130  # Standard code for SIGINT
                        process_completed.set()
                    break
            
            # Final update
            live.update(generate_display(final=True))
            live.refresh()  # Explicitly refresh
            
            # Sleep briefly to allow the display to update
            time.sleep(0.2)
            
            # Important: manually stop the live display but keep the output
            live.stop()
            
            return exit_code
            
        except Exception as e:
            # Handle errors
            if 'process' in locals() and process.poll() is None:
                process.terminate()
            
            live.stop()
            console.print(f"Error: {str(e)}", style="bold red")
            return 1


def main():
    """Run the procose CLI app."""
    # Check if there are command line arguments
    if len(sys.argv) < 3 or sys.argv[1] != "--":
        print("Usage: procose -- <command> [args...]")
        sys.exit(1)
    
    # Get the command to run (everything after --)
    command = sys.argv[2:]
    
    # Run the command with display
    exit_code = run_command_with_display(command)
    
    # Exit with the same code as the command
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
