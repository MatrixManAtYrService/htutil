#!/usr/bin/env python3
"""
Entry point for htutil release tests.
This script can be called from nix to run the container-based release tests.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Run the htutil release tests."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent

    # Run pytest with the release tests
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(script_dir / "test_release_containers.py"),
        "-v",
        "--tb=short",
        "-k",
        "not slow",  # Skip slow tests by default
    ]

    # Add any additional arguments passed to this script
    cmd.extend(sys.argv[1:])

    print("🚀 Running htutil release tests...")
    print(f"Command: {' '.join(cmd)}")

    # Run the tests
    result = subprocess.run(cmd)

    # Exit with the same code as pytest
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
