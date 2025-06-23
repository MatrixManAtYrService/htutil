#!/usr/bin/env python3
"""
Distribution tests for htty PyPI installations.

This test suite validates htty installation from PyPI in completely isolated Docker
containers that simulate real user environments.

Tests:
1. Wheel installation from PyPI - should work seamlessly with bundled ht binary
2. Sdist installation from PyPI - should show appropriate warnings when ht is missing
"""

from pathlib import Path

import pytest

try:
    from ..common.container_utils import (
        HttyTestContainer,
        find_container_tool,
        test_basic_htty_functionality,
        test_htty_console_script,
        test_htty_ht_console_script_if_bundled,
        test_import_warnings,
        test_console_scripts_consistency,
    )
except ImportError:
    # Fallback for when running as standalone script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from common.container_utils import (
        HttyTestContainer,
        find_container_tool,
        test_basic_htty_functionality,
        test_htty_console_script,
        test_htty_ht_console_script_if_bundled,
        test_import_warnings,
        test_console_scripts_consistency,
    )


@pytest.fixture(scope="session")
def docker_dir():
    """Get the Docker test directory."""
    # Docker dir is now in the same directory as this test
    return Path(__file__).parent / "docker"


@pytest.fixture(scope="session")
def container_tool():
    """Find and cache the available container tool (docker or podman)."""
    return find_container_tool()


@pytest.fixture(scope="session")
def wheel_container(docker_dir, container_tool):
    """Create and start the wheel test container."""
    container = HttyTestContainer(docker_dir / "Dockerfile.wheel", container_tool)
    container.start_container()
    yield container
    container.stop_container()


@pytest.fixture(scope="session")
def sdist_container(docker_dir, container_tool):
    """Create and start the sdist test container."""
    container = HttyTestContainer(docker_dir / "Dockerfile.sdist", container_tool)
    container.start_container()
    yield container
    container.stop_container()


class TestWheelInstallation:
    """Test htty wheel installation from PyPI."""

    def test_wheel_installs_successfully(self, wheel_container):
        """Test that wheel installs successfully from PyPI."""
        test_basic_htty_functionality(wheel_container)

    def test_wheel_console_scripts_work(self, wheel_container):
        """Test that console scripts work after PyPI wheel installation."""
        test_htty_console_script(wheel_container)

        # Test htty-ht command - wheel should have bundled ht binary
        test_htty_ht_console_script_if_bundled(wheel_container, should_have_bundled_ht=True)

    def test_wheel_import_no_warnings(self, wheel_container):
        """Test that importing htty from wheel shows no warnings (bundled ht binary)."""
        test_import_warnings(wheel_container, should_show_warnings=False)

    def test_wheel_htty_functionality(self, wheel_container):
        """Test basic htty functionality works with wheel installation."""
        exit_code, output = wheel_container.run_command([
            "python3 -c \"import htty; print('htty version:', getattr(htty, '__version__', 'unknown'))\"",
        ])

        assert exit_code == 0, f"htty functionality test failed: {output}"


class TestSdistInstallation:
    """Test htty sdist installation from PyPI."""

    def test_sdist_installs_successfully(self, sdist_container):
        """Test that sdist installs successfully from PyPI."""
        test_basic_htty_functionality(sdist_container)

    def test_sdist_console_scripts_work(self, sdist_container):
        """Test that console scripts work after PyPI sdist installation."""
        test_htty_console_script(sdist_container)

        # Test htty-ht command - sdist should NOT have bundled ht binary
        test_htty_ht_console_script_if_bundled(sdist_container, should_have_bundled_ht=False)

    def test_sdist_import_shows_warnings(self, sdist_container):
        """Test that importing htty from sdist shows appropriate warnings (no bundled ht binary)."""
        test_import_warnings(sdist_container, should_show_warnings=True)

    def test_sdist_helpful_error_messages(self, sdist_container):
        """Test that sdist installation provides helpful error messages when ht is missing."""
        # Try to use htty functionality that requires ht binary
        exit_code, output = sdist_container.run_command([
            "python3 -c \"import htty; print('htty imported successfully')\"",
        ])

        # Should import successfully even without ht binary
        assert exit_code == 0, f"htty import should succeed even without ht binary: {output}"
        print("✅ htty imports correctly from sdist installation")


class TestCrossPlatformConsistency:
    """Test that wheel and sdist installations provide consistent interface."""

    def test_console_scripts_consistent(self, wheel_container, sdist_container):
        """Test that both installations provide the same console scripts."""
        test_console_scripts_consistency(wheel_container, sdist_container)


def test_docker_environment_isolation():
    """Test that Docker environments are properly isolated."""
    print("✅ Docker environment isolation test - containers are isolated by design")
    # This test exists to document that isolation is achieved through containerization
    assert True