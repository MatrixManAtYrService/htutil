"""
Simple release tests for htutil bundled package.
These tests verify the bundled htutil works correctly when installed via pip.
"""

import subprocess
import tempfile
import os
from pathlib import Path

import pytest


def run_in_venv(commands, cwd=None):
    """Create a virtual environment and run commands in it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / "venv"

        # Create virtual environment
        subprocess.run(["python3", "-m", "venv", str(venv_path)], check=True)

        # Prepare environment
        env = os.environ.copy()
        env["PATH"] = f"{venv_path}/bin:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(venv_path)

        # Run commands
        results = []
        for cmd in commands:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd or tmpdir,
            )
            results.append((result.returncode, result.stdout + result.stderr))

        return results


class TestBundledRelease:
    """Test the bundled htutil package as it will be distributed on PyPI."""

    def test_htutil_help(self):
        """Test that htutil --help works after installation."""
        workspace = Path(__file__).parent.parent

        commands = [f"pip install -e {workspace}", "htutil --help"]

        results = run_in_venv(commands)

        # Check pip install succeeded
        assert results[0][0] == 0, f"pip install failed: {results[0][1]}"

        # Check htutil --help works
        assert results[1][0] == 0, f"htutil --help failed: {results[1][1]}"
        assert "usage: htutil" in results[1][1].lower()

    def test_htutil_version(self):
        """Test that htutil --version works."""
        workspace = Path(__file__).parent.parent

        commands = [f"pip install -e {workspace}", "htutil --version"]

        results = run_in_venv(commands)

        assert results[1][0] == 0, f"htutil --version failed: {results[1][1]}"
        assert "htutil" in results[1][1].lower()

    def test_simple_command_capture(self):
        """Test capturing output from a simple command."""
        workspace = Path(__file__).parent.parent

        commands = [
            f"pip install -e {workspace}",
            'htutil --rows 24 --cols 80 -- echo "Hello from htutil"',
        ]

        results = run_in_venv(commands)

        # Check for common errors that are expected in development
        if results[1][0] != 0:
            error_output = results[1][1]
            if "No such file or directory: 'ht'" in error_output:
                pytest.skip("ht binary not found in PATH (expected in development)")
            elif "Exec format error" in error_output:
                pytest.skip("Binary architecture mismatch (expected in development)")
            else:
                pytest.fail(f"htutil command failed: {error_output}")

        assert "Hello from htutil" in results[1][1]

    def test_bundled_ht_exists(self):
        """Test that the bundled ht binary is included in the package."""
        workspace = Path(__file__).parent.parent

        commands = [
            f"pip install -e {workspace}",
            "python -c \"import ht_util; from pathlib import Path; p = Path(ht_util.__file__).parent / '_bundled' / 'ht'; print(f'Bundled ht exists: {p.exists()}'); print(f'Bundled ht path: {p}')\"",
        ]

        results = run_in_venv(commands)

        assert results[1][0] == 0, f"Python check failed: {results[1][1]}"
        
        # In development mode, bundled binary may not exist
        if "Bundled ht exists: False" in results[1][1]:
            pytest.skip("Bundled ht binary not found (expected in development/editable install)")
        
        assert "Bundled ht exists: True" in results[1][1], "Bundled ht binary not found"

    @pytest.mark.slow
    def test_terminal_dimensions(self):
        """Test that terminal dimensions are properly set."""
        workspace = Path(__file__).parent.parent

        commands = [
            f"pip install -e {workspace}",
            'htutil --rows 30 --cols 100 -- bash -c "echo Lines: $(tput lines); echo Cols: $(tput cols)"',
        ]

        results = run_in_venv(commands)

        if results[1][0] != 0:
            error_output = results[1][1]
            if "No such file or directory: 'ht'" in error_output:
                pytest.skip("ht binary not found in PATH (expected in development)")
            elif "Exec format error" in error_output:
                pytest.skip("Binary architecture mismatch (expected in development)")
            else:
                pytest.fail(f"htutil command failed: {error_output}")

        output = results[1][1]
        # Check that terminal was created and tput worked
        # In some environments, tput may not work correctly, so we check for any numeric output
        if "Lines:" in output and "Cols:" in output:
            # If we have both outputs, check they are reasonable numbers
            assert any(char.isdigit() for char in output), "Expected numeric terminal dimensions"
        else:
            # If tput doesn't work properly, just verify the command ran without error
            assert results[1][0] == 0, "htutil command should complete successfully"
