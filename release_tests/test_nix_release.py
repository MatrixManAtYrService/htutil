"""
Nix-based release tests for htutil using nix-shell --pure with different Python versions.
This approach eliminates binary architecture issues and provides faster execution than containers.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple

import pytest


class NixPythonTestEnvironment:
    """Test environment using nix-shell --pure with specific Python versions."""
    
    def __init__(self, python_version: str, workspace_root: Path, htutil_wheel: Path = None):
        self.python_version = python_version
        self.workspace_root = workspace_root
        self.htutil_wheel = htutil_wheel
        self.temp_dir = None
        
    def __enter__(self):
        """Create temporary directory for virtualenv."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"htutil-nix-py{self.python_version}-"))
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_command(self, commands: List[str], install_htutil: bool = True, use_venv: bool = True) -> Tuple[int, str]:
        """Run commands in nix-shell --pure with specific Python version."""
        
        # Create the nix shell expression for the specific Python version
        nix_expr = f"""
with import <nixpkgs> {{}};
mkShell {{
  buildInputs = [ 
    python{self.python_version.replace('.', '')} 
    bash 
    coreutils 
    ncurses  # for tput
  ];
  shellHook = "";
}}
        """.strip()
        
        # Write the shell.nix to temp directory
        shell_nix = self.temp_dir / "shell.nix"
        shell_nix.write_text(nix_expr)
        
        # Create a script file instead of trying to pass complex commands as strings
        script_path = self.temp_dir / "test-script.sh"
        script_lines = ["#!/bin/bash", "set -euo pipefail", ""]
        
        if use_venv:
            # Create and activate virtual environment
            venv_path = self.temp_dir / "test-venv"
            script_lines.extend([
                f"python -m venv {venv_path}",
                f"source {venv_path}/bin/activate",
                "pip install --upgrade pip",
            ])
        
        if install_htutil:
            if self.htutil_wheel and self.htutil_wheel.exists():
                # Install htutil from the wheel (includes bundled ht binary)
                script_lines.append(f"pip install {self.htutil_wheel}")
            else:
                # Fallback to editable install from workspace
                script_lines.append(f"pip install -e {self.workspace_root}")
        
        # Handle complex Python commands by writing them to separate files
        for i, command in enumerate(commands):
            if command.strip().startswith('python -c "') and ('\\n' in command or len(command) > 100):
                # This is a multiline Python command - extract and write to file
                # Find the Python code between the quotes
                start_quote = command.find('"')
                end_quote = command.rfind('"')
                if start_quote != -1 and end_quote != -1 and start_quote != end_quote:
                    python_code = command[start_quote+1:end_quote]
                    python_file = self.temp_dir / f"python_script_{i}.py"
                    python_file.write_text(python_code)
                    script_lines.append(f"python {python_file}")
                else:
                    script_lines.append(command)
            else:
                script_lines.append(command)
        
        # Write the script file
        script_content = "\n".join(script_lines)
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        # Run in nix-shell --pure
        nix_cmd = [
            "nix-shell", "--pure", str(shell_nix),
            "--run", str(script_path)
        ]
        
        try:
            result = subprocess.run(
                nix_cmd,
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "Command timed out after 5 minutes"
        except Exception as e:
            return 1, f"Error running nix-shell command: {e}"


@pytest.fixture(scope="session")
def workspace_root():
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session") 
def htutil_wheel(workspace_root):
    """Build htutil wheel using nix and provide path to it."""
    print("🔨 Building htutil wheel with nix...")
    
    # Create a temporary directory for the wheel
    temp_dir = Path(tempfile.mkdtemp(prefix="htutil-wheel-"))
    
    try:
        # Build the wheel using nix
        nix_build_cmd = [
            "nix", "build", ".#htutil-wheel", 
            "--out-link", str(temp_dir / "result")
        ]
        
        result = subprocess.run(
            nix_build_cmd, 
            cwd=workspace_root,
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            pytest.fail(f"Failed to build htutil wheel: {result.stderr}")
        
        # Find the wheel file in the nix result
        result_path = temp_dir / "result"
        wheel_files = list(result_path.glob("*.whl"))
        
        if not wheel_files:
            pytest.fail(f"No wheel file found in {result_path}")
        
        wheel_file = wheel_files[0]
        print(f"✅ Built wheel: {wheel_file}")
        
        yield wheel_file
        
    finally:
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestNixPython310:
    """Test htutil functionality with Python 3.10 using nix-shell."""
    
    def test_cli_help(self, workspace_root, htutil_wheel):
        """Test that htutil --help works."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            exit_code, output = env.run_command(["htutil --help"])
            assert exit_code == 0, f"htutil --help failed: {output}"
            assert "usage: htutil" in output.lower(), "Expected usage message"
            assert "ht terminal emulation" in output.lower(), "Expected description"
    
    def test_cli_echo_capture(self, workspace_root, htutil_wheel):
        """Test capturing echo command output."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            commands = ['htutil --rows 5 --cols 40 -- echo "Test from Python 3.10"']
            exit_code, output = env.run_command(commands)
            
            # Should work without binary architecture issues since we're using native nix
            assert exit_code == 0, f"htutil echo failed: {output}"
            assert "Test from Python 3.10" in output, "Expected echo output"
    
    def test_cli_terminal_size(self, workspace_root, htutil_wheel):
        """Test that terminal size is properly set."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            commands = ['htutil --rows 10 --cols 50 -- bash -c "tput lines; tput cols"']
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"htutil tput failed: {output}"
            # Check that some numeric output is present (terminal dimensions)
            assert any(char.isdigit() for char in output), "Expected numeric terminal dimensions"
    
    def test_api_import(self, workspace_root, htutil_wheel):
        """Test that ht_util can be imported."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            commands = ['python -c "import ht_util; print(f\'Imported: {ht_util.__name__}\')"']
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"Import failed: {output}"
            assert "Imported: ht_util" in output
    
    def test_api_create_ht_instance(self, workspace_root, htutil_wheel):
        """Test creating an ht_process instance."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            commands = [
                """python -c "
from ht_util import ht_process
with ht_process(['echo', 'test'], rows=10, cols=40) as proc:
    print(f'Created ht_process instance: rows={proc.rows}, cols={proc.cols}')
    snapshot = proc.snapshot()
    print(f'Snapshot text length: {len(snapshot.text)}')
    print('ht_process context manager successful')
"
"""
            ]
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"ht_process creation failed: {output}"
            assert "Created ht_process instance: rows=10, cols=40" in output
            assert "ht_process context manager successful" in output
    
    def test_api_run_command(self, workspace_root, htutil_wheel):
        """Test running a command via Python API."""
        with NixPythonTestEnvironment("3.10", workspace_root, htutil_wheel) as env:
            commands = [
                """python -c "
from ht_util import run
import time
proc = run(['echo', 'Hello from API'], rows=5, cols=40)
time.sleep(0.5)  # Give command time to complete
snapshot = proc.snapshot()
print(f'Got snapshot with {len(snapshot.text)} chars')
proc.exit()
print('Command execution successful')
"
"""
            ]
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"Command execution failed: {output}"
            assert "Command execution successful" in output


class TestNixPython311:
    """Test htutil functionality with Python 3.11 using nix-shell."""
    
    def test_cli_help(self, workspace_root, htutil_wheel):
        """Test that htutil --help works."""
        with NixPythonTestEnvironment("3.11", workspace_root, htutil_wheel) as env:
            exit_code, output = env.run_command(["htutil --help"])
            assert exit_code == 0, f"htutil --help failed: {output}"
            assert "usage: htutil" in output.lower(), "Expected usage message"
            assert "ht terminal emulation" in output.lower(), "Expected description"
    
    def test_cli_echo_capture(self, workspace_root, htutil_wheel):
        """Test capturing echo command output."""
        with NixPythonTestEnvironment("3.11", workspace_root, htutil_wheel) as env:
            commands = ['htutil --rows 5 --cols 40 -- echo "Test from Python 3.11"']
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"htutil echo failed: {output}"
            assert "Test from Python 3.11" in output, "Expected echo output"
    
    def test_api_run_command(self, workspace_root, htutil_wheel):
        """Test running a command via Python API."""
        with NixPythonTestEnvironment("3.11", workspace_root, htutil_wheel) as env:
            commands = [
                """python -c "
from ht_util import run
import time
proc = run(['echo', 'Hello from API Python 3.11'], rows=5, cols=40)
time.sleep(0.5)
snapshot = proc.snapshot()
print(f'Got snapshot with {len(snapshot.text)} chars')
proc.exit()
print('Command execution successful')
"
"""
            ]
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"Command execution failed: {output}"
            assert "Command execution successful" in output


class TestNixPython312:
    """Test htutil functionality with Python 3.12 using nix-shell."""
    
    def test_cli_help(self, workspace_root, htutil_wheel):
        """Test that htutil --help works."""
        with NixPythonTestEnvironment("3.12", workspace_root, htutil_wheel) as env:
            exit_code, output = env.run_command(["htutil --help"])
            assert exit_code == 0, f"htutil --help failed: {output}"
            assert "usage: htutil" in output.lower(), "Expected usage message"
            assert "ht terminal emulation" in output.lower(), "Expected description"
    
    def test_cli_echo_capture(self, workspace_root, htutil_wheel):
        """Test capturing echo command output."""
        with NixPythonTestEnvironment("3.12", workspace_root, htutil_wheel) as env:
            commands = ['htutil --rows 5 --cols 40 -- echo "Test from Python 3.12"']
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"htutil echo failed: {output}"
            assert "Test from Python 3.12" in output, "Expected echo output"
    
    def test_api_run_command(self, workspace_root, htutil_wheel):
        """Test running a command via Python API."""
        with NixPythonTestEnvironment("3.12", workspace_root, htutil_wheel) as env:
            commands = [
                """python -c "
from ht_util import run
import time
proc = run(['echo', 'Hello from API Python 3.12'], rows=5, cols=40)
time.sleep(0.5)
snapshot = proc.snapshot()
print(f'Got snapshot with {len(snapshot.text)} chars')
proc.exit()
print('Command execution successful')
"
"""
            ]
            exit_code, output = env.run_command(commands)
            assert exit_code == 0, f"Command execution failed: {output}"
            assert "Command execution successful" in output


class TestNixPythonComparison:
    """Test that ensures functionality is consistent across Python versions."""
    
    def test_version_consistency(self, workspace_root, htutil_wheel):
        """Test that all Python versions produce similar results."""
        test_cmd = ['python -c "import ht_util; print(f\'Python: {ht_util.__name__} imported successfully\')"']
        
        results = {}
        for version in ["3.10", "3.11", "3.12"]:
            with NixPythonTestEnvironment(version, workspace_root, htutil_wheel) as env:
                exit_code, output = env.run_command(test_cmd)
                results[version] = (exit_code, output)
        
        # All should succeed
        for version, (exit_code, output) in results.items():
            assert exit_code == 0, f"Python {version} failed: {output}"
            assert "ht_util imported successfully" in output
        
        print(f"✅ All Python versions ({', '.join(results.keys())}) work consistently") 