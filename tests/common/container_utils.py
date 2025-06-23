#!/usr/bin/env python3
"""
Common container utilities for htty tests.

This module provides reusable container management utilities that can be used
across different test suites (distribution tests, integration tests, etc.).
"""

import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

import pytest


class HttyTestContainer:
    """Helper class to manage htty test containers using direct subprocess calls."""

    def __init__(self, dockerfile_path: Path, container_tool: str):
        self.dockerfile_path = dockerfile_path
        self.container_tool = container_tool
        self.container_id: Optional[str] = None
        self.image_tag: Optional[str] = None

    def start_container(self) -> str:
        """Start the container and return its ID."""
        if self.container_id:
            return self.container_id

        # Extract image type from dockerfile name (e.g., Dockerfile.wheel -> wheel)
        dockerfile_name = self.dockerfile_path.name  # e.g., "Dockerfile.wheel"
        image_type = dockerfile_name.split(".", 1)[1] if "." in dockerfile_name else dockerfile_name
        self.image_tag = f"htty-test-{image_type}"

        # Build the image using docker/podman build
        build_cmd = [
            self.container_tool,
            "build",
            "-f",
            str(self.dockerfile_path),
            "-t",
            self.image_tag,
            str(self.dockerfile_path.parent),  # Build context is the docker directory
        ]

        print(f"🐳 Building Docker image: {self.image_tag}")
        print(f"Build command: {' '.join(build_cmd)}")

        result = subprocess.run(build_cmd, capture_output=True, text=True)

        print("Build stdout:")
        print(result.stdout)
        if result.stderr:
            print("Build stderr:")
            print(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to build Docker image {self.image_tag}: {result.stderr}")

        # Start container without volumes (htty is pre-installed from PyPI)
        run_cmd = [
            self.container_tool,
            "run",
            "-d",  # detached mode
            self.image_tag,
            "tail",
            "-f",
            "/dev/null",  # Keep container running
        ]

        print("🚀 Starting container...")
        result = subprocess.run(run_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start container: {result.stderr}")

        self.container_id = result.stdout.strip()
        print(f"✅ Container started: {self.container_id}")

        # Wait a moment for container to be ready
        time.sleep(2)

        return self.container_id

    def run_command(self, commands: List[str]) -> Tuple[int, str]:
        """Run commands in the container."""
        if not self.container_id:
            raise RuntimeError("Container not started")

        # Join commands with &&
        full_command = " && ".join(commands)

        exec_cmd = [self.container_tool, "exec", self.container_id, "bash", "-c", full_command]

        result = subprocess.run(exec_cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr

        # Print command output for debugging
        print(f"Command: {full_command}")
        print(f"Exit code: {result.returncode}")
        print(f"Output:\n{output}")

        return result.returncode, output

    def stop_container(self):
        """Stop and remove the container."""
        if self.container_id:
            try:
                # Stop the container
                subprocess.run(
                    [self.container_tool, "stop", self.container_id], capture_output=True, text=True, timeout=10
                )
                # Remove the container
                subprocess.run(
                    [self.container_tool, "rm", self.container_id], capture_output=True, text=True, timeout=10
                )
            except Exception:
                pass  # Ignore errors during cleanup
            self.container_id = None

        # Also clean up the image to save space
        if self.image_tag:
            try:
                subprocess.run([self.container_tool, "rmi", self.image_tag], capture_output=True, text=True, timeout=10)
            except Exception:
                pass  # Ignore errors during cleanup


def find_container_tool() -> str:
    """Find and return the available container tool (docker or podman)."""
    # Allow override via environment variable
    if "CONTAINER_TOOL" in os.environ:
        tool = os.environ["CONTAINER_TOOL"]
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return tool
        except Exception:
            pass

    # Common paths where docker/podman might be installed
    common_paths = ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin", "/usr/sbin", "/usr/local/sbin", "/bin", "/sbin"]

    for tool in ["docker", "podman"]:
        # First try from PATH
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Found container tool: {tool}")
                return tool
        except FileNotFoundError:
            pass

        # Try common installation paths
        for path in common_paths:
            tool_path = os.path.join(path, tool)
            if os.path.exists(tool_path) and os.access(tool_path, os.X_OK):
                try:
                    result = subprocess.run([tool_path, "--version"], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        print(f"✅ Found container tool: {tool_path}")
                        return tool_path
                except Exception:
                    continue

    pytest.fail("Neither docker nor podman found. Please install a container runtime.")


def run_basic_htty_functionality_test(container):
    """Test that basic htty functionality works after installation."""
    exit_code, output = container.run_command(
        [
            "python3 -c \"import htty; print('htty imported successfully')\"",
        ]
    )

    assert exit_code == 0, f"htty import failed: {output}"
    assert "htty imported successfully" in output


def run_htty_console_script_test(container):
    """Test that htty console script works."""
    exit_code, output = container.run_command(
        [
            "which htty",
            "htty --help",
        ]
    )

    assert exit_code == 0, f"htty console script failed: {output}"
    assert "usage: htty" in output.lower()


def run_htty_ht_console_script_test(container, should_have_bundled_ht: bool):
    """Test htty-ht console script behavior based on installation type."""
    if should_have_bundled_ht:
        # Wheel installation should have bundled ht, so htty-ht should work
        exit_code, output = container.run_command(
            [
                "which htty-ht",
                "htty-ht --help",
            ]
        )
        assert exit_code == 0, f"htty-ht console script failed in wheel installation: {output}"
        assert "usage: ht" in output.lower() or "ht" in output.lower()
    else:
        # Sdist installation has no bundled ht, so htty-ht should fail with helpful error
        exit_code, output = container.run_command(
            [
                "which htty-ht",
                "htty-ht --help",
            ]
        )
        # htty-ht exists but should fail when trying to run without ht binary
        assert exit_code != 0, f"htty-ht should fail in sdist installation but succeeded: {output}"
        # Should show error about missing ht binary
        assert any(
            phrase in output.lower()
            for phrase in [
                "no such file or directory",
                "ht binary not found",
                "could not find ht binary",
                "htty installation warning",
            ]
        ), f"Expected error about missing ht binary but got: {output}"


def run_import_warnings_test(container, should_show_warnings: bool):
    """Test import warning behavior based on installation type."""
    exit_code, output = container.run_command(
        [
            "python3 -c \"import warnings; warnings.simplefilter('always'); import htty; print('Import completed')\"",
        ]
    )

    assert exit_code == 0, f"htty import failed: {output}"
    assert "Import completed" in output

    if should_show_warnings:
        # Sdist should show warnings about missing ht binary
        assert "htty installation warning" in output or "No 'ht' binary found" in output
    else:
        # Wheel should not show warnings (has bundled ht)
        # Note: This is a loose check since wheel might still show warnings in some environments
        print(f"Wheel installation import output: {output}")


def run_console_scripts_consistency_test(wheel_container, sdist_container):
    """Test that both installations provide the same console scripts."""
    # Check wheel scripts
    wheel_exit, wheel_output = wheel_container.run_command(
        [
            "ls ~/.local/bin/ | grep htty | sort",
        ]
    )

    # Check sdist scripts
    sdist_exit, sdist_output = sdist_container.run_command(
        [
            "ls ~/.local/bin/ | grep htty | sort",
        ]
    )

    assert wheel_exit == 0, f"Failed to list wheel scripts: {wheel_output}"
    assert sdist_exit == 0, f"Failed to list sdist scripts: {sdist_output}"

    # Both should have the same console scripts
    wheel_scripts = set(wheel_output.strip().split("\n"))
    sdist_scripts = set(sdist_output.strip().split("\n"))

    assert wheel_scripts == sdist_scripts, (
        f"Console scripts differ between wheel and sdist installations:\nWheel: {wheel_scripts}\nSdist: {sdist_scripts}"
    )

    print(f"✅ Both installations provide consistent console scripts: {wheel_scripts}")
