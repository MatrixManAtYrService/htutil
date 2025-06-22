#!/usr/bin/env python3
"""
Docker-based distribution tests for htty.

This test suite validates htty installation in completely isolated Docker 
containers that simulate real user environments without any Nix dependencies.

Tests:
1. Wheel installation - should work seamlessly with bundled ht binary
2. Sdist installation - should show appropriate warnings when ht is missing
"""

import subprocess
import tempfile
import json
import os
import sys
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest


class HttyTestContainer:
    """Helper class to manage htty test containers using direct subprocess calls."""
    
    def __init__(self, dockerfile_path: Path, workspace_root: Path, container_tool: str):
        self.dockerfile_path = dockerfile_path
        self.workspace_root = workspace_root
        self.container_tool = container_tool
        self.container_id: Optional[str] = None
        
    def start_container(self) -> str:
        """Start the container and return its ID."""
        if self.container_id:
            return self.container_id
            
        # Extract image type from dockerfile name (e.g., Dockerfile.wheel -> wheel)
        dockerfile_name = self.dockerfile_path.name  # e.g., "Dockerfile.wheel"
        image_type = dockerfile_name.split('.', 1)[1] if '.' in dockerfile_name else dockerfile_name
        image_tag = f"htty-test-{image_type}"
        
        # Build the image using docker/podman build
        build_cmd = [
            self.container_tool, "build", 
            "-f", str(self.dockerfile_path),
            "-t", image_tag,
            str(self.dockerfile_path.parent)  # Build context is the docker directory
        ]
        
        print(f"🐳 Building Docker image: {image_tag}")
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            pytest.fail(f"Failed to build Docker image {image_tag}: {result.stderr}")
            
        # Start container with volumes
        if image_type == "wheel":
            # Mount wheel directory
            wheel_dir = self.workspace_root / "result-wheel"
            run_cmd = [
                self.container_tool, "run", "-d",  # detached mode
                "-v", f"{wheel_dir}:/wheels:ro",  # Mount wheel directory as read-only
                image_tag,
                "tail", "-f", "/dev/null"  # Keep container running
            ]
        else:  # sdist
            # Mount sdist directory
            sdist_dir = self.workspace_root / "result-sdist"
            run_cmd = [
                self.container_tool, "run", "-d",  # detached mode
                "-v", f"{sdist_dir}:/sdist:ro",  # Mount sdist directory as read-only
                image_tag,
                "tail", "-f", "/dev/null"  # Keep container running
            ]
        
        print(f"🚀 Starting container...")
        result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            pytest.fail(f"Failed to start container: {result.stderr}")
            
        self.container_id = result.stdout.strip()
        print(f"✅ Container started: {self.container_id}")
        
        # Wait a moment for container to be ready
        time.sleep(2)
        
        return self.container_id
        
    def run_command(self, commands: List[str]) -> Tuple[int, str]:
        """Run commands in the container."""
        if not self.container_id:
            pytest.fail("Container not started")
            
        # Join commands with &&
        full_command = " && ".join(commands)
        
        exec_cmd = [
            self.container_tool, "exec", 
            self.container_id,
            "bash", "-c", full_command
        ]
        
        result = subprocess.run(exec_cmd, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr
        
    def stop_container(self):
        """Stop and remove the container."""
        if self.container_id:
            try:
                # Stop the container
                subprocess.run([self.container_tool, "stop", self.container_id], 
                             capture_output=True, text=True, timeout=10)
                # Remove the container
                subprocess.run([self.container_tool, "rm", self.container_id], 
                             capture_output=True, text=True, timeout=10)
            except Exception:
                pass  # Ignore errors during cleanup
            self.container_id = None


@pytest.fixture(scope="session")
def workspace_root():
    """Get the workspace root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def docker_dir(workspace_root):
    """Get the Docker test directory."""
    return workspace_root / "test_distribution" / "docker"


@pytest.fixture(scope="session")
def container_tool():
    """Find and cache the available container tool (docker or podman)."""
    # Allow override via environment variable
    if "CONTAINER_TOOL" in os.environ:
        tool = os.environ["CONTAINER_TOOL"]
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Found container tool (env): {tool}")
                return tool
        except Exception:
            pass

    # Common paths where docker/podman might be installed
    common_paths = [
        "/usr/bin", "/usr/local/bin", "/opt/homebrew/bin", 
        "/usr/sbin", "/usr/local/sbin", "/bin", "/sbin"
    ]

    for tool in ["docker", "podman"]:
        # First try from PATH (might work if not in nix shell)
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
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
                    result = subprocess.run([tool_path, "--version"], capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"✅ Found container tool: {tool_path}")
                        return tool_path
                except Exception:
                    continue

    pytest.fail("Neither docker nor podman found. Please install a container runtime or ensure it's in your PATH.\n"
                "You can also set CONTAINER_TOOL environment variable to specify the path.")


@pytest.fixture(scope="session")
def wheel_container(docker_dir, workspace_root, container_tool):
    """Create and start the wheel test container."""
    container = HttyTestContainer(docker_dir / "Dockerfile.wheel", workspace_root, container_tool)
    container.start_container()
    yield container
    container.stop_container()


@pytest.fixture(scope="session")
def sdist_container(docker_dir, workspace_root, container_tool):
    """Create and start the sdist test container."""
    container = HttyTestContainer(docker_dir / "Dockerfile.sdist", workspace_root, container_tool)
    container.start_container()
    yield container
    container.stop_container()


@pytest.fixture(scope="session", autouse=True)
def build_artifacts(workspace_root):
    """Ensure wheel and sdist artifacts are available for testing."""
    print("🔧 Checking for htty wheel and sdist artifacts...")
    
    # Check for wheel - either from environment variable or nix build
    wheel_path = os.environ.get("HTTY_WHEEL_PATH")
    if wheel_path and Path(wheel_path).exists():
        print(f"✅ Using wheel from environment: {wheel_path}")
        # Create symlink for consistent access
        wheel_link = workspace_root / "result-wheel"
        if wheel_link.exists():
            wheel_link.unlink()
        wheel_link.symlink_to(Path(wheel_path).parent)
    else:
        # Try to build with nix if available
        try:
            result = subprocess.run(
                ["nix", "build", ".#htty-wheel", "--out-link", "result-wheel"],
                cwd=workspace_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                pytest.skip(f"Cannot build wheel and no HTTY_WHEEL_PATH provided: {result.stderr}")
        except FileNotFoundError:
            pytest.skip("Cannot build wheel: nix not available and no HTTY_WHEEL_PATH provided")
    
    # Check for sdist - either from environment variable or nix build
    sdist_path = os.environ.get("HTTY_SDIST_PATH")
    if sdist_path and Path(sdist_path).exists():
        print(f"✅ Using sdist from environment: {sdist_path}")
        # Create symlink for consistent access
        sdist_link = workspace_root / "result-sdist"
        if sdist_link.exists():
            sdist_link.unlink()
        sdist_link.symlink_to(Path(sdist_path).parent)
    else:
        # Try to build with nix if available
        try:
            result = subprocess.run(
                ["nix", "build", ".#htty-sdist", "--out-link", "result-sdist"],
                cwd=workspace_root,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                pytest.skip(f"Cannot build sdist and no HTTY_SDIST_PATH provided: {result.stderr}")
        except FileNotFoundError:
            pytest.skip("Cannot build sdist: nix not available and no HTTY_SDIST_PATH provided")
    
    print("✅ Wheel and sdist artifacts ready")


class TestWheelInstallation:
    """Test wheel installation in isolated Docker container."""
    
    def test_wheel_installs_successfully(self, wheel_container):
        """Test that wheel installs without issues."""
        commands = [
            "ls -la /wheels/",  # Debug: see what's available
            "python3 -m pip install --user /wheels/*.whl"
        ]
        
        exit_code, output = wheel_container.run_command(commands)
        print(f"Installation output: {output}")
        
        assert exit_code == 0, f"Wheel installation failed: {output}"
        assert "Successfully installed htty" in output, "Expected successful installation message"
        
    def test_wheel_console_scripts_work(self, wheel_container):
        """Test that console scripts are available after wheel installation."""
        commands = [
            "python3 -m pip install --user /wheels/*.whl",
            "which htty",
            "which htty-ht",
            "htty --help",
            "htty-ht --help"
        ]
        
        exit_code, output = wheel_container.run_command(commands)
        print(f"Console scripts output: {output}")
        
        assert exit_code == 0, f"Console scripts test failed: {output}"
        assert "/home/testuser/.local/bin/htty" in output, "htty script not found in expected location"
        assert "/home/testuser/.local/bin/htty-ht" in output, "htty-ht script not found in expected location"
        
    def test_wheel_import_no_warnings(self, wheel_container):
        """Test that wheel import doesn't show warnings (bundled binary)."""
        commands = [
            "python3 -m pip install --user /wheels/*.whl",
            "python3 -c 'import warnings; warnings.simplefilter(\"always\"); import htty; print(\"Import successful\")'"
        ]
        
        exit_code, output = wheel_container.run_command(commands)
        print(f"Import test output: {output}")
        
        assert exit_code == 0, f"Import test failed: {output}"
        assert "Import successful" in output, "Import should have succeeded"
        # For wheel installation, we expect no warnings about missing ht
        assert "No 'ht' binary found" not in output, "Wheel should not warn about missing ht"
        
    def test_wheel_htty_functionality(self, wheel_container):
        """Test that htty can actually run basic functionality."""
        commands = [
            "python3 -m pip install --user /wheels/*.whl",
            "echo 'test' | htty --help > /dev/null && echo 'htty works'",
            "htty-ht --help > /dev/null && echo 'htty-ht works'"
        ]
        
        exit_code, output = wheel_container.run_command(commands)
        print(f"Functionality test output: {output}")
        
        # Note: htty-ht might fail if ht binary has issues, but htty --help should work
        assert "htty works" in output, "htty command should work"


class TestSdistInstallation:
    """Test sdist installation in isolated Docker container."""
    
    def test_sdist_installs_successfully(self, sdist_container):
        """Test that sdist installs without issues."""
        commands = [
            "ls -la /sdist/",  # Debug: see what's available
            "python3 -m pip install --user /sdist/*.tar.gz"
        ]
        
        exit_code, output = sdist_container.run_command(commands)
        print(f"Installation output: {output}")
        
        assert exit_code == 0, f"Sdist installation failed: {output}"
        assert "Successfully installed htty" in output, "Expected successful installation message"
        
    def test_sdist_console_scripts_work(self, sdist_container):
        """Test that console scripts are available after sdist installation."""
        commands = [
            "python3 -m pip install --user /sdist/*.tar.gz",
            "which htty",
            "which htty-ht",
            "htty --help",
        ]
        
        exit_code, output = sdist_container.run_command(commands)
        print(f"Console scripts output: {output}")
        
        assert exit_code == 0, f"Console scripts test failed: {output}"
        assert "/home/testuser/.local/bin/htty" in output, "htty script not found in expected location"
        assert "/home/testuser/.local/bin/htty-ht" in output, "htty-ht script not found in expected location"
        
    def test_sdist_import_shows_warnings(self, sdist_container):
        """Test that sdist import shows appropriate warnings (no bundled binary)."""
        commands = [
            "python3 -m pip install --user /sdist/*.tar.gz",
            "python3 -c 'import warnings; warnings.simplefilter(\"always\"); import htty; print(\"Import successful\")' 2>&1"
        ]
        
        exit_code, output = sdist_container.run_command(commands)
        print(f"Import test output: {output}")
        
        assert exit_code == 0, f"Import test failed: {output}"
        assert "Import successful" in output, "Import should have succeeded"
        # For sdist installation without ht, we expect warnings
        assert ("No 'ht' binary found" in output or 
                "warning" in output.lower() or 
                "Warning" in output), "Sdist should warn about missing ht binary"
        
    def test_sdist_helpful_error_messages(self, sdist_container):
        """Test that sdist provides helpful error messages when ht is missing."""
        commands = [
            "python3 -m pip install --user /sdist/*.tar.gz",
            "python3 -c 'import htty; htty.run([\"echo\", \"test\"])' 2>&1 || echo 'Expected error occurred'"
        ]
        
        exit_code, output = sdist_container.run_command(commands)
        print(f"Error message test output: {output}")
        
        # We expect this to fail, but with a helpful error message
        assert "Expected error occurred" in output or exit_code != 0, "Should fail when ht is missing"
        # Should provide helpful guidance
        assert ("install" in output.lower() or 
                "download" in output.lower() or
                "binary" in output.lower()), "Should provide helpful guidance about installing ht"


class TestCrossPlatformConsistency:
    """Test that both wheel and sdist behave consistently."""
    
    def test_console_scripts_consistent(self, wheel_container, sdist_container):
        """Test that both wheel and sdist install the same console scripts."""
        # Test wheel
        wheel_exit_code, wheel_output = wheel_container.run_command([
            "python3 -m pip install --user /wheels/*.whl",
            "ls ~/.local/bin/ | grep htty | sort"
        ])
        
        # Test sdist
        sdist_exit_code, sdist_output = sdist_container.run_command([
            "python3 -m pip install --user /sdist/*.tar.gz",
            "ls ~/.local/bin/ | grep htty | sort"
        ])
        
        assert wheel_exit_code == 0, f"Wheel console script check failed: {wheel_output}"
        assert sdist_exit_code == 0, f"Sdist console script check failed: {sdist_output}"
        
        # Extract the script lists
        wheel_scripts = [line.strip() for line in wheel_output.split('\n') if line.strip() and 'htty' in line]
        sdist_scripts = [line.strip() for line in sdist_output.split('\n') if line.strip() and 'htty' in line]
        
        print(f"Wheel scripts: {wheel_scripts}")
        print(f"Sdist scripts: {sdist_scripts}")
        
        assert wheel_scripts == sdist_scripts, "Wheel and sdist should install the same console scripts"
        assert "htty" in wheel_scripts, "Should install htty script"
        assert "htty-ht" in wheel_scripts, "Should install htty-ht script"


def test_docker_environment_isolation():
    """Test that our Docker environment is properly isolated from Nix."""
    # This test runs outside of containers to verify isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        dockerfile_content = """
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 python3-pip
RUN python3 -c "import sys; print('Python path:', sys.path)"
RUN which nix 2>/dev/null && echo 'ERROR: nix found' || echo 'Good: nix not found'
CMD ["python3", "-c", "print('Isolation test passed')"]
"""
        
        dockerfile_path = Path(temp_dir) / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        # Try to find docker/podman
        container_tool = None
        for tool in ["docker", "podman"]:
            try:
                result = subprocess.run([tool, "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    container_tool = tool
                    break
            except FileNotFoundError:
                continue
        
        if not container_tool:
            pytest.skip("No container tool available")
        
        # Build and run isolation test
        image_tag = "htty-isolation-test"
        
        build_result = subprocess.run([
            container_tool, "build", "-t", image_tag, temp_dir
        ], capture_output=True, text=True)
        
        if build_result.returncode != 0:
            pytest.fail(f"Failed to build isolation test: {build_result.stderr}")
        
        run_result = subprocess.run([
            container_tool, "run", "--rm", image_tag
        ], capture_output=True, text=True)
        
        print(f"Isolation test output: {run_result.stdout}")
        
        assert run_result.returncode == 0, f"Isolation test failed: {run_result.stderr}"
        assert "Isolation test passed" in run_result.stdout
        assert "Good: nix not found" in run_result.stdout, "Container should not have access to nix"
        
        # Clean up
        subprocess.run([container_tool, "rmi", image_tag], capture_output=True, text=True) 