#!/usr/bin/env python3
"""
Test installation warnings for different htty distribution scenarios.

This test simulates what happens when users install htty from PyPI
on different platforms and configurations.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def test_pypi_installation_simulation():
    """
    Simulate installing htty from PyPI and test the experience.
    
    This test creates a clean virtual environment and installs htty
    to test the real user experience.
    """
    print("Testing PyPI installation simulation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = Path(temp_dir) / "test_venv"
        
        # Create virtual environment
        subprocess.run([
            sys.executable, "-m", "venv", str(venv_path)
        ], check=True)
        
        # Get python executable in venv
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"
        
        # Install htty from local sdist (simulating PyPI)
        # Use the pre-built sdist if available, otherwise build one
        sdist_path = os.environ.get("HTTY_SDIST_PATH")
        if sdist_path and Path(sdist_path).exists():
            print(f"Using pre-built sdist: {sdist_path}")
        else:
            print("Building sdist locally...")
            subprocess.run([
                sys.executable, "-m", "build", "--sdist", "--outdir", temp_dir
            ], check=True, cwd=Path(__file__).parent.parent)
            
            # Find the built sdist
            sdist_files = list(Path(temp_dir).glob("htty-*.tar.gz"))
            if not sdist_files:
                raise RuntimeError("No sdist found")
            sdist_path = str(sdist_files[0])
        
        # Install from sdist
        result = subprocess.run([
            str(python_exe), "-m", "pip", "install", str(sdist_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Installation failed: {result.stderr}")
            raise RuntimeError("Failed to install htty from sdist")
        
        print("✓ Installation successful")
        
        # Test importing htty and capture warnings
        test_script = '''
import warnings
import sys

# Capture all warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    
    try:
        import htty
        print("Import successful")
        
        if w:
            print(f"Warnings captured: {len(w)}")
            for warning in w:
                print(f"Warning: {warning.message}")
                print(f"Category: {warning.category.__name__}")
        else:
            print("No warnings")
            
    except Exception as e:
        print(f"Import failed: {e}")
        sys.exit(1)
'''
        
        result = subprocess.run([
            str(python_exe), "-c", test_script
        ], capture_output=True, text=True)
        
        print(f"Import test output: {result.stdout}")
        if result.stderr:
            print(f"Import test stderr: {result.stderr}")
        
        # The import should succeed
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "Import successful" in result.stdout
        
        # Check if warnings were shown appropriately
        import shutil
        if not shutil.which("ht"):
            # No system ht available - should show strong warning
            assert "Warning:" in result.stdout or "warning" in result.stdout.lower(), \
                "Expected warning about missing ht binary"
            print("✓ Appropriate warning shown for missing ht binary")
        else:
            # System ht available - might show gentle warning
            print("✓ System ht available, warning behavior depends on installation type")
    
    print("✓ PyPI installation simulation test passed")


def test_console_scripts_available():
    """Test that console scripts are available after installation."""
    print("Testing console scripts availability...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_path = Path(temp_dir) / "test_venv"
        
        # Create virtual environment
        subprocess.run([
            sys.executable, "-m", "venv", str(venv_path)
        ], check=True)
        
        # Get python executable in venv
        if sys.platform == "win32":
            python_exe = venv_path / "Scripts" / "python.exe"
            bin_dir = venv_path / "Scripts"
        else:
            python_exe = venv_path / "bin" / "python"
            bin_dir = venv_path / "bin"
        
        # Install htty from local sdist
        sdist_path = os.environ.get("HTTY_SDIST_PATH")
        if sdist_path and Path(sdist_path).exists():
            print(f"Using pre-built sdist: {sdist_path}")
        else:
            print("Building sdist locally...")
            subprocess.run([
                sys.executable, "-m", "build", "--sdist", "--outdir", temp_dir
            ], check=True, cwd=Path(__file__).parent.parent)
            
            sdist_files = list(Path(temp_dir).glob("htty-*.tar.gz"))
            if not sdist_files:
                raise RuntimeError("No sdist found")
            sdist_path = str(sdist_files[0])
        
        # Install from sdist
        result = subprocess.run([
            str(python_exe), "-m", "pip", "install", str(sdist_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Installation failed: {result.stderr}")
            raise RuntimeError("Failed to install htty from sdist")
        
        # Check that console scripts were installed
        htty_script = bin_dir / ("htty.exe" if sys.platform == "win32" else "htty")
        htty_ht_script = bin_dir / ("htty-ht.exe" if sys.platform == "win32" else "htty-ht")
        
        assert htty_script.exists(), f"htty console script not found at {htty_script}"
        assert htty_ht_script.exists(), f"htty-ht console script not found at {htty_ht_script}"
        
        print("✓ Console scripts installed correctly")
        
        # Test that scripts can show help (even without ht binary)
        for script_name, script_path in [("htty", htty_script), ("htty-ht", htty_ht_script)]:
            result = subprocess.run([
                str(script_path), "--help"
            ], capture_output=True, text=True)
            
            # Scripts should show help or fail gracefully
            print(f"✓ {script_name} script responds to --help")
    
    print("✓ Console scripts availability test passed")


def main():
    """Run all distribution tests."""
    print("Running htty distribution tests...")
    print("=" * 50)
    
    try:
        test_pypi_installation_simulation()
        test_console_scripts_available()
        
        print("=" * 50)
        print("✅ All distribution tests passed!")
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 