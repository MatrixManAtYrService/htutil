#!/usr/bin/env python3
"""
Manual runner for Docker-based distribution tests.

This script can be run manually when Docker is available to test htty
installation in completely isolated Docker containers.

Usage:
    python distribution_tests/run_docker_tests.py

Prerequisites:
    - Docker or Podman installed
    - Built wheel and sdist artifacts (run: nix build .#htty-wheel .#htty-sdist)
"""

import os
import subprocess
import sys
from pathlib import Path


def find_container_tool():
    """Find available container tool (docker or podman)."""
    for tool in ["docker", "podman"]:
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Found container tool: {tool}")
                return tool
        except FileNotFoundError:
            continue
    
    print("❌ Neither docker nor podman found.")
    print("Please install Docker or Podman to run these tests.")
    sys.exit(1)


def check_artifacts():
    """Check that wheel and sdist artifacts are available."""
    workspace = Path(__file__).parent.parent
    
    # Check for wheel
    wheel_paths = list(workspace.glob("result-wheel/*.whl"))
    if not wheel_paths:
        print("❌ No wheel found. Please run: nix build .#htty-wheel")
        sys.exit(1)
    
    # Check for sdist
    sdist_paths = list(workspace.glob("result-sdist/*.tar.gz"))
    if not sdist_paths:
        print("❌ No sdist found. Please run: nix build .#htty-sdist")
        sys.exit(1)
    
    print(f"✅ Found wheel: {wheel_paths[0]}")
    print(f"✅ Found sdist: {sdist_paths[0]}")
    
    return wheel_paths[0], sdist_paths[0]


def run_docker_tests(container_tool, wheel_path, sdist_path):
    """Run the Docker-based distribution tests."""
    workspace = Path(__file__).parent.parent
    
    # Set environment variables for the tests
    env = os.environ.copy()
    env["CONTAINER_TOOL"] = container_tool
    env["HTTY_WHEEL_PATH"] = str(wheel_path)
    env["HTTY_SDIST_PATH"] = str(sdist_path)
    
    # Run the Docker tests using pytest
    cmd = [
        sys.executable, "-m", "pytest", 
        "-v", "-s",
        str(workspace / "distribution_tests" / "test_docker_isolation.py")
    ]
    
    print(f"🧪 Running Docker tests...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, env=env, cwd=workspace)
    
    if result.returncode == 0:
        print("✅ All Docker tests passed!")
    else:
        print("❌ Some Docker tests failed.")
        sys.exit(1)


def main():
    """Main function."""
    print("🐳 Docker-based htty Distribution Tests")
    print("=" * 50)
    
    # Check prerequisites
    container_tool = find_container_tool()
    wheel_path, sdist_path = check_artifacts()
    
    # Run tests
    run_docker_tests(container_tool, wheel_path, sdist_path)


if __name__ == "__main__":
    main() 