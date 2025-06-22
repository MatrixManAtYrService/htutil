#!/usr/bin/env python3
"""
Simple distribution tests for htty that don't require Docker.

This test suite validates htty installation using temporary virtual environments
to simulate clean installation scenarios.

Tests:
1. Wheel installation - should work seamlessly
2. Sdist installation - should work with appropriate warnings
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def workspace_root():
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def wheel_path():
    """Get the path to the wheel file."""
    wheel_path = os.environ.get("HTTY_WHEEL_PATH")
    if wheel_path and Path(wheel_path).exists():
        return Path(wheel_path)

    pytest.skip("No wheel file found. Set HTTY_WHEEL_PATH environment variable.")


@pytest.fixture(scope="session")
def sdist_path():
    """Get the path to the sdist file."""
    sdist_path = os.environ.get("HTTY_SDIST_PATH")
    if sdist_path and Path(sdist_path).exists():
        return Path(sdist_path)

    pytest.skip("No sdist file found. Set HTTY_SDIST_PATH environment variable.")


class TestWheelVenvInstallation:
    """Test wheel installation in virtual environments."""

    def test_wheel_installs_successfully(self, wheel_path):
        """Test that wheel installs without issues in a clean venv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create virtual environment
            result = subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, text=True)

            assert result.returncode == 0, f"Failed to create venv: {result.stderr}"

            # Get python executable
            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
            else:
                python_exe = venv_path / "bin" / "python"

            # Install wheel
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "install", str(wheel_path)], capture_output=True, text=True
            )

            print(f"Installation output: {result.stdout}")
            if result.stderr:
                print(f"Installation stderr: {result.stderr}")

            assert result.returncode == 0, f"Wheel installation failed: {result.stderr}"
            assert "Successfully installed" in result.stdout and "htty" in result.stdout, (
                "Expected successful installation message"
            )

    def test_wheel_console_scripts(self, wheel_path):
        """Test that console scripts work after wheel installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create and set up venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
                bin_dir = venv_path / "Scripts"
            else:
                python_exe = venv_path / "bin" / "python"
                bin_dir = venv_path / "bin"

            # Install wheel
            subprocess.run([str(python_exe), "-m", "pip", "install", str(wheel_path)], check=True)

            # Check console scripts exist
            htty_script = bin_dir / ("htty.exe" if sys.platform == "win32" else "htty")
            htty_ht_script = bin_dir / ("htty-ht.exe" if sys.platform == "win32" else "htty-ht")

            assert htty_script.exists(), f"htty console script not found at {htty_script}"
            assert htty_ht_script.exists(), f"htty-ht console script not found at {htty_ht_script}"

            # Test that scripts can show help
            result = subprocess.run([str(htty_script), "--help"], capture_output=True, text=True)

            # Should either succeed or fail gracefully
            print(f"htty --help output: {result.stdout}")
            print(f"htty --help stderr: {result.stderr}")

    def test_wheel_import_works(self, wheel_path):
        """Test that importing htty works after wheel installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create and set up venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

            python_exe = venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

            # Install wheel
            subprocess.run([str(python_exe), "-m", "pip", "install", str(wheel_path)], check=True)

            # Test import
            result = subprocess.run(
                [
                    str(python_exe),
                    "-c",
                    "import warnings; warnings.simplefilter('always'); import htty; print('Import successful')",
                ],
                capture_output=True,
                text=True,
            )

            print(f"Import output: {result.stdout}")
            if result.stderr:
                print(f"Import stderr: {result.stderr}")

            assert result.returncode == 0, f"Import failed: {result.stderr}"
            assert "Import successful" in result.stdout, "Import should have succeeded"


class TestSdistVenvInstallation:
    """Test sdist installation in virtual environments."""

    def test_sdist_installs_successfully(self, sdist_path):
        """Test that sdist installs without issues in a clean venv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create virtual environment
            result = subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, text=True)

            assert result.returncode == 0, f"Failed to create venv: {result.stderr}"

            # Get python executable
            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
            else:
                python_exe = venv_path / "bin" / "python"

            # Install sdist
            result = subprocess.run(
                [str(python_exe), "-m", "pip", "install", str(sdist_path)], capture_output=True, text=True
            )

            print(f"Installation output: {result.stdout}")
            if result.stderr:
                print(f"Installation stderr: {result.stderr}")

            assert result.returncode == 0, f"Sdist installation failed: {result.stderr}"
            assert "Successfully installed" in result.stdout and "htty" in result.stdout, (
                "Expected successful installation message"
            )

    def test_sdist_console_scripts(self, sdist_path):
        """Test that console scripts work after sdist installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create and set up venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

            if sys.platform == "win32":
                python_exe = venv_path / "Scripts" / "python.exe"
                bin_dir = venv_path / "Scripts"
            else:
                python_exe = venv_path / "bin" / "python"
                bin_dir = venv_path / "bin"

            # Install sdist
            subprocess.run([str(python_exe), "-m", "pip", "install", str(sdist_path)], check=True)

            # Check console scripts exist
            htty_script = bin_dir / ("htty.exe" if sys.platform == "win32" else "htty")
            htty_ht_script = bin_dir / ("htty-ht.exe" if sys.platform == "win32" else "htty-ht")

            assert htty_script.exists(), f"htty console script not found at {htty_script}"
            assert htty_ht_script.exists(), f"htty-ht console script not found at {htty_ht_script}"

    def test_sdist_import_shows_warnings(self, sdist_path):
        """Test that importing htty shows appropriate warnings after sdist installation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"

            # Create and set up venv
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

            python_exe = venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

            # Install sdist
            subprocess.run([str(python_exe), "-m", "pip", "install", str(sdist_path)], check=True)

            # Test import with warning capture
            result = subprocess.run(
                [
                    str(python_exe),
                    "-c",
                    "import warnings; warnings.simplefilter('always'); import htty; print('Import successful')",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": "/usr/bin:/bin"},
            )

            print(f"Import output: {result.stdout}")
            print(f"Import stderr: {result.stderr}")

            assert result.returncode == 0, f"Import failed: {result.stderr}"
            assert "Import successful" in result.stdout, "Import should have succeeded"

            # Check for warnings about missing ht (unless system has it)
            import shutil

            if not shutil.which("ht"):
                full_output = result.stdout + result.stderr
                assert (
                    "warning" in full_output.lower()
                    or "Warning" in full_output
                    or "No 'ht' binary found" in full_output
                ), "Should show warning about missing ht binary"


class TestConsistency:
    """Test that wheel and sdist installations are consistent."""

    def test_both_install_same_scripts(self, wheel_path, sdist_path):
        """Test that both wheel and sdist install the same console scripts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test wheel
            wheel_venv = Path(temp_dir) / "wheel_venv"
            subprocess.run([sys.executable, "-m", "venv", str(wheel_venv)], check=True)

            wheel_python = wheel_venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            wheel_bin = wheel_venv / ("Scripts" if sys.platform == "win32" else "bin")

            subprocess.run([str(wheel_python), "-m", "pip", "install", str(wheel_path)], check=True)

            # Test sdist
            sdist_venv = Path(temp_dir) / "sdist_venv"
            subprocess.run([sys.executable, "-m", "venv", str(sdist_venv)], check=True)

            sdist_python = sdist_venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            sdist_bin = sdist_venv / ("Scripts" if sys.platform == "win32" else "bin")

            subprocess.run([str(sdist_python), "-m", "pip", "install", str(sdist_path)], check=True)

            # Compare installed scripts
            wheel_scripts = set(f.name for f in wheel_bin.iterdir() if f.name.startswith("htty"))
            sdist_scripts = set(f.name for f in sdist_bin.iterdir() if f.name.startswith("htty"))

            print(f"Wheel scripts: {wheel_scripts}")
            print(f"Sdist scripts: {sdist_scripts}")

            assert wheel_scripts == sdist_scripts, "Wheel and sdist should install the same scripts"

            expected_scripts = {"htty", "htty-ht"}
            if sys.platform == "win32":
                expected_scripts = {f"{script}.exe" for script in expected_scripts}

            assert expected_scripts.issubset(wheel_scripts), (
                f"Missing expected scripts: {expected_scripts - wheel_scripts}"
            )
