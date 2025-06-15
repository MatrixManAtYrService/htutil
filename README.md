WARNING: this repo is a sandbox, it makes no promises and is currently a bit of a mess.
I'll remove this warning if it becomes something worth using

# Procose

Syntactic sugar for Python subprocesses with an inline terminal UI.

This project provides a Python wrapper around the [`ht`](https://github.com/andyk/ht) terminal emulator tool, allowing you to programmatically interact with and test command-line applications.

## Features

- Interactive CLI interface similar to fzf
- Run commands in a structured way with terminal emulation
- View command output directly in the terminal
- Capture terminal snapshots with both plain text and styled HTML
- Send keystrokes programmatically to interactive applications
- Test terminal-based applications reliably

## Core API Usage

### Basic Usage with `run` and `snapshot`

```python
from htutil import run, Press

# Start a subprocess with terminal emulation
proc = run("python my_script.py", rows=10, cols=40)

# Take a snapshot of the current terminal state
snapshot = proc.snapshot()
print(snapshot.text)      # Plain text output
print(snapshot.html)      # HTML with ANSI color styling
print(snapshot.raw_seq)   # Raw ANSI sequences

# Send keystrokes to the process
proc.send_keys(Press.ENTER)
proc.send_keys("hello world")
proc.send_keys([Press.CTRL_C, Press.ENTER])

# Exit cleanly (terminates subprocess if needed, then ht process)
proc.exit()
```

### Key Parameters

- `rows`/`cols`: Terminal dimensions (height/width)
- `no_exit`: Default `True` - keeps `ht` running after subprocess exits for final state examination

### Context Manager (Recommended)

```python
from htutil import ht_process, Press

with ht_process("python interactive_app.py", rows=5, cols=20) as proc:
    proc.send_keys("input data")
    proc.send_keys(Press.ENTER)
    
    snapshot = proc.snapshot()
    assert "expected output" in snapshot.text
    # Automatic cleanup when exiting context
```

### Exit Behavior

The `exit()` method reliably terminates both the subprocess and ht process:

- If subprocess is still running → terminates it first, then exits ht
- If subprocess already finished → just exits ht
- Always returns 0 for successful termination
- Handles both `no_exit=True` and `no_exit=False` modes

## Development Setup

### Running Tests

Use the nix development shell for a consistent environment:

```bash
# Enter the development shell
nix develop

# Run all tests
uv run pytest -vs tests/test_htutil.py

# Run specific test
uv run pytest -vs tests/test_htutil.py::test_exit_while_subprocess_running
```

### Example Test Pattern

```python
def test_interactive_app():
    proc = run("python my_app.py", rows=5, cols=20)
    
    # Initial state
    snapshot = proc.snapshot()
    assert "Welcome" in snapshot.text
    
    # Interact with the app
    proc.send_keys("user input")
    proc.send_keys(Press.ENTER)
    
    # Verify response
    snapshot = proc.snapshot()
    assert "expected response" in snapshot.text
    
    # Clean exit
    proc.exit()
```

## References for Future Development

- **HT Tool**: See [github.com/andyk/ht](https://github.com/andyk/ht) for the underlying terminal emulator
- **Test Examples**: See `tests/test_htutil.py` for comprehensive usage patterns and edge cases
- **API Documentation**: See `src/htutil/ht.py` for full implementation details
- **Key Definitions**: See `src/htutil/keys.py` for all supported keyboard inputs

## Architecture

This project wraps the `ht` tool which:
1. Spawns a subprocess in a PTY (pseudo-terminal)
2. Captures all terminal output including ANSI escape sequences
3. Provides a JSON API for sending keystrokes and taking snapshots
4. Supports both interactive use and programmatic control

The Python wrapper (`htutil`) provides:
- High-level API for process management
- Snapshot objects with text/HTML/raw formats
- Enum-based key input system
- Automatic resource cleanup
- Comprehensive test utilities

## Usage

```bash
# Run the procose inline interface
procose
```
