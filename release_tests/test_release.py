"""
Release tests for htty using Python's virtualenv.
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
    """Environment for testing htty wheel installations across Python versions."""

    def __init__(self, python_version: str, workspace_root: Path, htty_wheel: Path):
        self.python_version = python_version
        self.workspace_root = workspace_root
        self.htty_wheel = htty_wheel
        self.setup_complete = False
        self.venv_dir = None
        self.python_executable = None

    def setup(self):
        """Set up a virtualenv and install the htty wheel - this tests the real wheel experience."""
        if self.setup_complete:
            return

        print(f"🐍 Setting up wheel test environment for Python {self.python_version}")

        # Create a temporary directory for the virtualenv
        self.venv_dir = Path(tempfile.mkdtemp(prefix=f"htty-wheel-test-py{self.python_version}-"))

        # Create virtualenv using the specified Python version
        python_bin = f"python{self.python_version}"
        print(f"📦 Creating virtualenv with {python_bin}")

        try:
            # Verify Python version is available
            result = subprocess.run(
                [python_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Python {self.python_version} not available: {result.stderr}")
            print(f"✅ Using Python: {result.stdout.strip()}")

            # Create virtualenv
            venv_result = subprocess.run(
                [python_bin, "-m", "venv", str(self.venv_dir)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if venv_result.returncode != 0:
                raise RuntimeError(f"Failed to create virtualenv: {venv_result.stderr}")

            # Set up Python executable path for the virtualenv
            if os.name == "nt":  # Windows
                self.python_executable = self.venv_dir / "Scripts" / "python.exe"
            else:  # Unix-like
                self.python_executable = self.venv_dir / "bin" / "python"

            if not self.python_executable.exists():
                raise RuntimeError(f"Virtualenv Python executable not found: {self.python_executable}")

            print(f"✅ Virtualenv created at: {self.venv_dir}")

            # Look for pre-downloaded wheels in the Nix environment
            wheels_dir = None

            # Check for wheel cache directory from environment variable
            wheel_cache_dir = os.environ.get("WHEEL_CACHE_DIR")
            if wheel_cache_dir:
                cache_path = Path(wheel_cache_dir)
                wheels_dir = cache_path / "wheels"
                if not wheels_dir.exists():
                    print(f"⚠️  WHEEL_CACHE_DIR set to {wheel_cache_dir} but wheels directory not found")
                    wheels_dir = None

            # Install the htty wheel - this is what we're actually testing!
            print(f"🎯 Installing htty wheel: {self.htty_wheel}")

            install_cmd = [str(self.python_executable), "-m", "pip", "install", str(self.htty_wheel)]

            # If we found pre-downloaded wheels, use them
            if wheels_dir and wheels_dir.exists():
                print(f"📦 Using pre-downloaded wheels from: {wheels_dir}")
                install_cmd.extend(["--find-links", str(wheels_dir), "--no-index"])
            else:
                print("⚠️  No pre-downloaded wheels found, will try to download dependencies")

            install_result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if install_result.returncode != 0:
                raise RuntimeError(f"Failed to install htty wheel: {install_result.stderr}")

            print("✅ htty wheel installed successfully")
            if install_result.stdout:
                print(f"📦 Installation output: {install_result.stdout}")

        except FileNotFoundError:
            raise RuntimeError(f"Python {self.python_version} not found in PATH")

        print(f"✅ Wheel test environment ready for Python {self.python_version}")
        self.setup_complete = True

    def run_command(self, command: str) -> Tuple[int, str]:
        """Run a command in the virtualenv where htty wheel is installed."""
        if not self.setup_complete:
            self.setup()

        print(f"💻 Executing in virtualenv: {command}")

        try:
            # Run command in the virtualenv
            # We need to activate the virtualenv environment variables
            env = os.environ.copy()

            # Set virtualenv paths
            if os.name == "nt":  # Windows
                env["PATH"] = f"{self.venv_dir / 'Scripts'}{os.pathsep}{env.get('PATH', '')}"
            else:  # Unix-like
                env["PATH"] = f"{self.venv_dir / 'bin'}{os.pathsep}{env.get('PATH', '')}"

            env["VIRTUAL_ENV"] = str(self.venv_dir)

            # Remove any PYTHONHOME that might interfere
            env.pop("PYTHONHOME", None)

            result = subprocess.run(
                command,
                shell=True,
                cwd=self.venv_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
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
        """Run a Python script in the virtualenv."""
        if not self.setup_complete:
            self.setup()
        assert self.venv_dir is not None

        # Create a temporary Python file in the virtualenv directory
        python_file = self.venv_dir / f"script_{hash(python_code) % 10000}.py"
        python_file.write_text(python_code)
        print("🐍 Executing Python script in virtualenv:")
        print(f"    {python_code.strip()}")

        # Run the Python script using the virtualenv's Python
        return self.run_command(f"python {python_file}")

    def cleanup(self):
        """Clean up the virtualenv directory."""
        if self.venv_dir and self.venv_dir.exists():
            shutil.rmtree(self.venv_dir, ignore_errors=True)
            print(f"🧹 Cleaned up virtualenv for Python {self.python_version}")

    def copy_file(self, source: Path, destination: str):
        """Copy a file to the virtualenv working directory."""
        if not self.setup_complete:
            self.setup()
        assert self.venv_dir is not None
        print(f"💾 Copying file: {source} to {destination}")

        # Copy the file to the virtualenv directory
        destination_path = self.venv_dir / destination
        shutil.copy(source, destination_path)

        print(f"✅ File copied successfully: {destination_path}")


@pytest.fixture(scope="session")
def workspace_root():
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def htty_wheel():
    """Get htty wheel path from environment variable."""
    wheel_path = os.environ.get("htty_WHEEL_PATH")
    if not wheel_path:
        pytest.fail(
            "htty_WHEEL_PATH environment variable is not set. Please set it to the path of the built htty wheel."
        )
    wheel_file = Path(wheel_path)
    if not wheel_file.exists():
        pytest.fail(f"htty_WHEEL_PATH does not exist: {wheel_file}")
    return wheel_file


@pytest.fixture(scope="function")
def python_env(request, workspace_root, htty_wheel):
    """Create a Python environment for the current test's Python version."""
    # Get the python_version from the current test's parameters
    python_version = request.node.callspec.params["python_version"]

    env = PythonEnvironment(python_version, workspace_root, htty_wheel)
    env.setup()  # Set up for this specific test

    yield env

    env.cleanup()


@pytest.mark.parametrize("python_version", PYTHON_VERSIONS)
class TestNixPython:
    """Test htty functionality across Python versions using Python's virtualenv."""

    def test_cli_help(self, python_version, python_env):
        """Test that htty --help works."""
        exit_code, output = python_env.run_command("htty --help")
        assert exit_code == 0, f"htty --help failed: {output}"
        assert "usage: htty" in output.lower(), "Expected usage message"
        assert "ht terminal emulation" in output.lower(), "Expected description"

    def test_cli_echo_capture(self, python_version, python_env):
        """Test capturing echo command output."""
        exit_code, output = python_env.run_command(
            f'htty --rows 5 --cols 40 -- echo "Test from Python {python_version}"'
        )

        # Should work without binary architecture issues since we're using native nix
        assert exit_code == 0, f"htty echo failed: {output}"
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
            f"htty --rows 5 --cols 4 -- python{python_version} number_triangle.py"
        )
        assert exit_code == 0, f"htty test failed: {output}"

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
        """Test that htty can be imported."""
        exit_code, output = python_env.run_command("python -c \"import htty; print(f'Imported: {htty.__name__}')\"")
        assert exit_code == 0, f"Import failed: {output}"
        assert "Imported: htty" in output

    def test_api_create_ht_instance(self, python_version, python_env):
        """Test creating an ht_process instance."""
        command = """python -c "
from htty import ht_process
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
from htty import run
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

    def test_version_consistency(self, workspace_root, htty_wheel):
        """Test that all Python versions produce similar results."""
        test_cmd = "python -c \"import htty; print(f'Python: {htty.__name__} imported successfully')\""

        results = {}
        for version in PYTHON_VERSIONS:
            env = PythonEnvironment(version, workspace_root, htty_wheel)
            env.setup()
            try:
                exit_code, output = env.run_command(test_cmd)
                results[version] = (exit_code, output)
            finally:
                env.cleanup()

        # All should succeed
        for version, (exit_code, output) in results.items():
            assert exit_code == 0, f"Python {version} failed: {output}"
            assert "htty imported successfully" in output

        print(f"✅ All Python versions ({', '.join(results.keys())}) work consistently")
