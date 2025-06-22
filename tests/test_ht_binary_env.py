"""Tests for HTTY_HT_BIN environment variable functionality."""

import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pytest import LoggingPlugin, MonkeyPatch

# Import the new ht_binary context manager from ht.py
from htty.ht import ht_binary


class TestHttyHTBin:
    """Test cases for HTTY_HT_BIN environment variable handling."""

    def test_no_env_var_no_bundled_uses_system_ht(self, monkeypatch: "MonkeyPatch", caplog: "LoggingPlugin") -> None:
        """Test that without HTTY_HT_BIN and no bundled ht, system ht is used."""
        # Set logging level to capture WARNING messages
        with caplog.at_level("WARNING", logger="htty.ht"):
            # Ensure HTTY_HT_BIN is not set
            monkeypatch.delenv("HTTY_HT_BIN", raising=False)

            # Mock importlib.resources to simulate no bundled ht
            with patch("importlib.resources.files") as mock_files:
                mock_files.side_effect = ImportError("No bundled resources")

                # Mock shutil.which to simulate system ht being available
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = "/usr/bin/ht"

                    with ht_binary() as ht:
                        assert ht.path == "/usr/bin/ht"
                        assert "Using system ht binary from PATH: /usr/bin/ht" in caplog.text
                        assert "Expect trouble if this ht does not have the changes in this fork" in caplog.text

    def test_valid_env_var_is_used(self, monkeypatch: "MonkeyPatch", caplog: "LoggingPlugin") -> None:
        """Test that a valid HTTY_HT_BIN path is used."""
        with caplog.at_level("INFO", logger="htty.ht"):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"#!/bin/sh\necho 'mock ht'\n")
                tmp_path = tmp.name

            # Make it executable
            os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)

            # Set the environment variable
            monkeypatch.setenv("HTTY_HT_BIN", tmp_path)

            try:
                with ht_binary() as ht:
                    assert ht.path == tmp_path
                    assert "Using user-specified ht binary from HTTY_HT_BIN" in caplog.text
            finally:
                os.unlink(tmp_path)

    def test_nonexistent_env_var_raises_error(self, monkeypatch: "MonkeyPatch") -> None:
        """Test that nonexistent HTTY_HT_BIN path raises helpful error."""
        # Set environment variable to nonexistent path
        nonexistent_path = "/nonexistent/path/to/ht"
        monkeypatch.setenv("HTTY_HT_BIN", nonexistent_path)

        with pytest.raises(RuntimeError) as exc_info:
            with ht_binary():
                pass

        error_msg = str(exc_info.value)
        assert f"HTTY_HT_BIN='{nonexistent_path}' is not a valid executable file" in error_msg
        assert "Please check that the path exists and is executable" in error_msg

    def test_non_executable_env_var_raises_error(self, monkeypatch: "MonkeyPatch") -> None:
        """Test that non-executable HTTY_HT_BIN path raises helpful error."""
        # Create a temporary non-executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"not executable")
            tmp_path = tmp.name

        # Ensure it's NOT executable
        os.chmod(tmp_path, 0o644)

        # Set the environment variable
        monkeypatch.setenv("HTTY_HT_BIN", tmp_path)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                with ht_binary():
                    pass

            error_msg = str(exc_info.value)
            assert f"HTTY_HT_BIN='{tmp_path}' is not a valid executable file" in error_msg
            assert "Please check that the path exists and is executable" in error_msg
        finally:
            os.unlink(tmp_path)

    def test_bundled_ht_used_when_present(self, monkeypatch: "MonkeyPatch", caplog: "LoggingPlugin") -> None:
        """Test that bundled ht is used when present and no env var is set."""
        # Set logging level to capture INFO messages
        with caplog.at_level("INFO", logger="htty.ht"):
            # Ensure HTTY_HT_BIN is not set
            monkeypatch.delenv("HTTY_HT_BIN", raising=False)

            # Mock the entire _try_bundled_binary function to simulate finding bundled ht
            def mock_try_bundled():
                import logging

                logger = logging.getLogger("htty.ht")
                logger.info("Using bundled ht binary")
                return "/tmp/ht_test"

            with patch("htty.ht._try_bundled_binary", side_effect=mock_try_bundled):
                with ht_binary() as ht:
                    assert ht.path == "/tmp/ht_test"
                    assert "Using bundled ht binary" in caplog.text

    def test_env_var_overrides_bundled(self, monkeypatch: "MonkeyPatch", caplog: "LoggingPlugin") -> None:
        """Test that HTTY_HT_BIN overrides bundled ht when both exist."""
        # Set logging level to capture INFO messages
        with caplog.at_level("INFO", logger="htty.ht"):
            # Create a temporary executable file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"#!/bin/sh\necho 'custom ht'\n")
                tmp_path = tmp.name

            # Make it executable
            os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)

            # Set the environment variable
            monkeypatch.setenv("HTTY_HT_BIN", tmp_path)

            try:
                # Mock the bundled ht to also exist
                with patch("pathlib.Path.exists") as mock_exists:

                    def exists_side_effect(path: Path) -> bool:
                        if "_bundled" in str(path):
                            return True
                        return os.path.exists(path)

                    mock_exists.side_effect = exists_side_effect

                    with patch("pathlib.Path.is_file", return_value=True):
                        with ht_binary() as ht:
                            assert ht.path == tmp_path
                            assert "Using user-specified ht binary from HTTY_HT_BIN" in caplog.text
            finally:
                os.unlink(tmp_path)

    def test_empty_env_var_ignored(self, monkeypatch: "MonkeyPatch", caplog: "LoggingPlugin") -> None:
        """Test that empty HTTY_HT_BIN is ignored and falls back to system ht."""
        # Set logging level to capture WARNING messages
        with caplog.at_level("WARNING", logger="htty.ht"):
            monkeypatch.setenv("HTTY_HT_BIN", "")

            # Mock importlib.resources to simulate no bundled ht
            with patch("importlib.resources.files") as mock_files:
                mock_files.side_effect = ImportError("No bundled resources")

                # Mock shutil.which to simulate system ht being available
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = "/usr/bin/ht"

                    with ht_binary() as ht:
                        assert ht.path == "/usr/bin/ht"
                        assert "Using system ht binary from PATH: /usr/bin/ht" in caplog.text
                        assert "Expect trouble if this ht does not have the changes in this fork" in caplog.text

    def test_helpful_error_message_content(self, monkeypatch: "MonkeyPatch") -> None:
        """Test that helpful error message is shown when no ht binary is found anywhere."""
        # Ensure HTTY_HT_BIN is not set
        monkeypatch.delenv("HTTY_HT_BIN", raising=False)

        # Mock importlib.resources to simulate no bundled ht
        with patch("importlib.resources.files") as mock_files:
            mock_files.side_effect = ImportError("No bundled resources")

            # Mock shutil.which to simulate no system ht available
            with patch("shutil.which") as mock_which:
                mock_which.return_value = None

                with pytest.raises(RuntimeError) as exc_info:
                    with ht_binary():
                        pass

                error_msg = str(exc_info.value)
                # Check that helpful error message parts are present
                expected_parts = [
                    "Could not find ht binary",
                    "You installed from source",
                    "Install ht separately",
                    "Set HTTY_HT_BIN to point to ht binary",
                    "https://github.com/andyk/ht",
                ]
                for part in expected_parts:
                    assert part in error_msg, f"Missing expected part: {part}"

    def test_ht_binary_helper_methods(self, monkeypatch: "MonkeyPatch") -> None:
        """Test that HTBinary helper methods work correctly."""
        # Create a temporary executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"#!/bin/sh\necho 'mock ht'\n")
            tmp_path = tmp.name

        # Make it executable
        os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)

        # Set the environment variable
        monkeypatch.setenv("HTTY_HT_BIN", tmp_path)

        try:
            with ht_binary() as ht:
                # Test build_command method
                cmd = ht.build_command("--help", "--version")
                assert cmd == [tmp_path, "--help", "--version"]

                # Test that run_subprocess method returns a Popen object
                import subprocess

                proc = ht.run_subprocess("--help", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                assert isinstance(proc, subprocess.Popen)
                proc.terminate()  # Clean up
                proc.wait()
        finally:
            os.unlink(tmp_path)


class TestHTBinaryIntegration:
    """Integration tests for ht binary resolution in actual htty usage."""

    @pytest.mark.skipif(
        not Path("src/htty/ht.py").exists(),
        reason="ht.py not found - run from project root",
    )
    def test_ht_binary_context_manager_usage(self):
        """Test that the ht_binary context manager can be used successfully."""
        # Test that we can use the context manager without errors
        with ht_binary() as ht:
            assert hasattr(ht, "path")
            assert hasattr(ht, "build_command")
            assert hasattr(ht, "run_subprocess")
            assert isinstance(ht.path, str)
            assert len(ht.path) > 0
