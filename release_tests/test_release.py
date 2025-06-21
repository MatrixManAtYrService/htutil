"""
Release tests for htutil using Python's virtualenv.
Run pytest with `-s` to see print output.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Tuple

import pytest

PYTHON_VERSIONS = ["3.10", "3.11", "3.12"]


class PythonEnvironment:
    """Reusable Python environment for a specific Python version."""

    def __init__(self, python_version: str, workspace_root: Path, htutil_wheel: Path):
        self.python_version = python_version
        self.workspace_root = workspace_root
        self.htutil_wheel = htutil_wheel
        self.temp_dir = None
        self.venv_path = None
        self.setup_complete = False

    def setup(self):
        """Set up the environment once - reusable across multiple commands."""
        if self.setup_complete:
            return

        print(f"🐍 Setting up environment for Python {self.python_version}")

        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"htutil-py{self.python_version}-"))
        self.venv_path = self.temp_dir / "test-venv"

        setup_script = self.temp_dir / "setup.sh"
        setup_commands = [
            "#!/bin/bash",
            "set -euo pipefail",
            f"python{self.python_version} -m venv {self.venv_path}",
            f"source {self.venv_path}/bin/activate",
            "pip install --upgrade pip",
            f"pip install {self.htutil_wheel}",
            "python --version",  # Verify we're using the correct Python version
            "echo 'Setup complete for Python {self.python_version}'",
        ]

        setup_script.write_text("\n".join(setup_commands))
        setup_script.chmod(0o755)

        print(f"📦 Setting up virtualenv for Python {self.python_version}...")
        result = subprocess.run(
            str(setup_script),
            cwd=self.temp_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to set up environment: {result.stderr}")

        print(f"✅ Environment ready for Python {self.python_version}")
        self.setup_complete = True

    def run_command(self, command: str) -> Tuple[int, str]:
        """Run a command in the prepared virtualenv environment."""
        if not self.setup_complete:
            self.setup()
        assert self.temp_dir is not None
        assert self.venv_path is not None
        print(f"💻 Executing: {command}")

        # Crea te script that activates venv and runs command
        script_path = self.temp_dir / f"cmd_{hash(command) % 10000}.sh"
        script_content = dedent(
            f"""#!/bin/bash
                set -euo pipefail
                source {self.venv_path}/bin/activate
                {command}
                """
        )
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        try:
            result = subprocess.run(
                str(script_path),
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.stdout:
                print("📤 STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("⚠️  STDERR:")
                print(result.stderr)

            print(f"🏁 Command completed with exit code: {result.returncode}")

            return result.returncode, result.stdout + (result.stderr if result.stderr else "")
        except subprocess.TimeoutExpired:
            print("⏰ Command timed out after 5 minutes")
            return 1, "Command timed out after 5 minutes"
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return 1, f"Error running command: {e}"

    def run_command_with_script(self, python_code: str) -> Tuple[int, str]:
        """Run a Python script in the prepared virtualenv environment."""
        if not self.setup_complete:
            self.setup()
        assert self.temp_dir is not None
        # Create a temporary Python file
        python_file = self.temp_dir / f"script_{hash(python_code) % 10000}.py"
        python_file.write_text(python_code)
        print("🐍 Executing Python script:")
        print(f"    {python_code.strip()}")
        return self.run_command(f"python {python_file}")

    def cleanup(self):
        """Clean up the temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"🧹 Cleaned up environment for Python {self.python_version}")

    def copy_file(self, source: Path, destination: str):
        """Copy a file to the virtualenv environment."""
        if not self.setup_complete:
            self.setup()
        assert self.temp_dir is not None
        print(f"💾 Copying file: {source} to {destination}")

        # Copy the file to the temp directory
        destination_path = self.temp_dir / destination
        shutil.copy(source, destination_path)

        print(f"✅ File copied successfully: {destination_path}")


@pytest.fixture(scope="session")
def workspace_root():
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def htutil_wheel():
    """Get htutil wheel path from environment variable."""
    wheel_path = os.environ.get("HTUTIL_WHEEL_PATH")
    if not wheel_path:
        pytest.fail(
            "HTUTIL_WHEEL_PATH environment variable is not set. Please set it to the path of the built htutil wheel."
        )
    wheel_file = Path(wheel_path)
    if not wheel_file.exists():
        pytest.fail(f"HTUTIL_WHEEL_PATH does not exist: {wheel_file}")
    return wheel_file


@pytest.fixture(scope="function")
def python_env(request, workspace_root, htutil_wheel):
    """Create a Python environment for the current test's Python version."""
    # Get the python_version from the current test's parameters
    python_version = request.node.callspec.params["python_version"]

    env = PythonEnvironment(python_version, workspace_root, htutil_wheel)
    env.setup()  # Set up for this specific test

    yield env

    env.cleanup()


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
class TestNixPython:
    """Test htutil functionality across Python versions using Python's virtualenv."""

    def test_cli_help(self, python_version, python_env):
        """Test that htutil --help works."""
        exit_code, output = python_env.run_command("htutil --help")
        assert exit_code == 0, f"htutil --help failed: {output}"
        assert "usage: htutil" in output.lower(), "Expected usage message"
        assert "ht terminal emulation" in output.lower(), "Expected description"

    def test_cli_echo_capture(self, python_version, python_env):
        """Test capturing echo command output."""
        exit_code, output = python_env.run_command(
            f'htutil --rows 5 --cols 40 -- echo "Test from Python {python_version}"'
        )

        # Should work without binary architecture issues since we're using native nix
        assert exit_code == 0, f"htutil echo failed: {output}"
        assert f"Test from Python {python_version}" in output, "Expected echo output"

    def test_cli_terminal_size(self, python_version, python_env):
        """Test that terminal size is properly set by checking text wrapping."""
        # Copy the number_triangle.py script to the nix environment's working directory
        script_path = Path(__file__).parent / "number_triangle.py"
        python_env.copy_file(script_path, "number_triangle.py")

        # Use 5 rows × 4 cols to test both dimensions
        # The script outputs:
        #   1
        #   22
        #   333
        #   4444
        #   55555
        # But with a 5x4 terminal we should see:
        #   333    (first two lines scrolled out)
        #   4444   (fits perfectly)
        #   5555   (wraps to next line)
        #   5      (remaining digit)
        #          (trailing newline)
        exit_code, output = python_env.run_command(
            f"htutil --rows 5 --cols 4 -- python{python_version} number_triangle.py"
        )
        assert exit_code == 0, f"htutil test failed: {output}"

        # Split output into lines and filter out empty lines and separators
        lines = [line for line in output.split("\n") if line and line != "----"]

        # We should have exactly 4 lines with the following pattern:
        # Line 1: "333"    (from original line 3)
        # Line 2: "4444"   (from original line 4)
        # Line 3: "5555"   (from original line 5, wrapped)
        # Line 4: "5"      (from original line 5, remaining digit)
        assert len(lines) == 4, dedent(
            f"""
            Expected exactly 4 lines, got {len(lines)}:
            {lines}
            """
        )

        # Check each line matches the expected pattern
        assert lines[0] == "333", f"Expected '333', got '{lines[0]}'"
        assert lines[1] == "4444", f"Expected '4444', got '{lines[1]}'"
        assert lines[2] == "5555", f"Expected '5555', got '{lines[2]}'"
        assert lines[3] == "5", f"Expected '5', got '{lines[3]}'"

    def test_api_import(self, python_version, python_env):
        """Test that htutil can be imported."""
        exit_code, output = python_env.run_command("python -c \"import htutil; print(f'Imported: {htutil.__name__}')\"")
        assert exit_code == 0, f"Import failed: {output}"
        assert "Imported: htutil" in output

    def test_api_create_ht_instance(self, python_version, python_env):
        """Test creating an ht_process instance."""
        command = """python -c "
from htutil import ht_process
with ht_process(['echo', 'test'], rows=10, cols=40) as proc:
    print(f'Created ht_process instance: rows={proc.rows}, cols={proc.cols}')
    snapshot = proc.snapshot()
    print(f'Snapshot text length: {len(snapshot.text)}')
    print('ht_process context manager successful')
"
"""
        exit_code, output = python_env.run_command(command)
        assert exit_code == 0, f"ht_process creation failed: {output}"
        assert "Created ht_process instance: rows=10, cols=40" in output
        assert "ht_process context manager successful" in output

    def test_api_run_command(self, python_version, python_env):
        """Test running a command via Python API."""
        command = f"""python -c "
from htutil import run
import time
proc = run(['echo', 'Hello from API Python {python_version}'], rows=5, cols=40)
time.sleep(0.5)  # Give command time to complete
snapshot = proc.snapshot()
print(f'Got snapshot with {{len(snapshot.text)}} chars')
proc.exit()
print('Command execution successful')
"
"""
        exit_code, output = python_env.run_command(command)
        assert exit_code == 0, f"Command execution failed: {output}"
        assert "Command execution successful" in output


class TestNixPythonConsistency:
    """Test that ensures functionality is consistent across Python versions."""

    def test_version_consistency(self, workspace_root, htutil_wheel):
        """Test that all Python versions produce similar results."""
        test_cmd = "python -c \"import htutil; print(f'Python: {htutil.__name__} imported successfully')\""

        results = {}
        for version in PYTHON_VERSIONS:
            env = PythonEnvironment(version, workspace_root, htutil_wheel)
            env.setup()
            try:
                exit_code, output = env.run_command(test_cmd)
                results[version] = (exit_code, output)
            finally:
                env.cleanup()

        # All should succeed
        for version, (exit_code, output) in results.items():
            assert exit_code == 0, f"Python {version} failed: {output}"
            assert "htutil imported successfully" in output

        print(f"✅ All Python versions ({', '.join(results.keys())}) work consistently")
