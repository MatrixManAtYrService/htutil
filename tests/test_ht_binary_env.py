"""Tests for HTUTIL_HT_BIN environment variable functionality."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
import stat

# Import the actual get_ht_binary function from ht.py
from htutil.ht import get_ht_binary


class TestHTUtilHTBin:
    """Test cases for HTUTIL_HT_BIN environment variable handling."""

    def test_no_env_var_no_bundled_uses_system_ht(self, monkeypatch, caplog):
        """Test that without HTUTIL_HT_BIN and no bundled ht, system ht is used."""
        # Set logging level to capture WARNING messages
        with caplog.at_level("WARNING", logger="htutil.ht"):
            # Ensure HTUTIL_HT_BIN is not set
            monkeypatch.delenv("HTUTIL_HT_BIN", raising=False)

            # Mock importlib.resources to simulate no bundled ht
            with patch("importlib.resources.files") as mock_files:
                mock_files.side_effect = ImportError("No bundled resources")

                # Mock shutil.which to simulate system ht being available
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = "/usr/bin/ht"

                    result = get_ht_binary()
                    assert result == "/usr/bin/ht"
                    assert (
                        "Using system ht binary from PATH: /usr/bin/ht" in caplog.text
                    )
                    assert "Version and compatibility are not guaranteed" in caplog.text

    def test_valid_env_var_is_used(self, monkeypatch, caplog):
        """Test that a valid HTUTIL_HT_BIN path is used."""
        # Set logging level to capture INFO messages
        with caplog.at_level("INFO", logger="htutil.ht"):
            # Create a temporary executable file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"#!/bin/sh\necho 'mock ht'\n")
                tmp_path = tmp.name

            # Make it executable
            os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)

            # Set the environment variable
            monkeypatch.setenv("HTUTIL_HT_BIN", tmp_path)

            try:
                result = get_ht_binary()
                assert result == tmp_path
                assert (
                    "Using user-specified ht binary from HTUTIL_HT_BIN" in caplog.text
                )
            finally:
                os.unlink(tmp_path)

    def test_nonexistent_env_var_raises_error(self, monkeypatch):
        """Test that nonexistent HTUTIL_HT_BIN path raises helpful error."""
        # Set environment variable to nonexistent path
        nonexistent_path = "/nonexistent/path/to/ht"
        monkeypatch.setenv("HTUTIL_HT_BIN", nonexistent_path)

        with pytest.raises(RuntimeError) as exc_info:
            get_ht_binary()

        error_msg = str(exc_info.value)
        assert (
            f"HTUTIL_HT_BIN='{nonexistent_path}' is not a valid executable file"
            in error_msg
        )
        assert "Please check that the path exists and is executable" in error_msg

    def test_non_executable_env_var_raises_error(self, monkeypatch):
        """Test that non-executable HTUTIL_HT_BIN path raises helpful error."""
        # Create a temporary non-executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"not executable")
            tmp_path = tmp.name

        # Ensure it's NOT executable
        os.chmod(tmp_path, 0o644)

        # Set the environment variable
        monkeypatch.setenv("HTUTIL_HT_BIN", tmp_path)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                get_ht_binary()

            error_msg = str(exc_info.value)
            assert (
                f"HTUTIL_HT_BIN='{tmp_path}' is not a valid executable file"
                in error_msg
            )
            assert "Please check that the path exists and is executable" in error_msg
        finally:
            os.unlink(tmp_path)

    def test_bundled_ht_used_when_present(self, monkeypatch, caplog):
        """Test that bundled ht is used when present and no env var is set."""
        # Set logging level to capture INFO messages
        with caplog.at_level("INFO", logger="htutil.ht"):
            # Ensure HTUTIL_HT_BIN is not set
            monkeypatch.delenv("HTUTIL_HT_BIN", raising=False)

            # Mock importlib.resources to simulate bundled ht exists
            with patch("importlib.resources.files") as mock_files:
                # Mock the files() method and resource access
                mock_ht_resource = mock_files.return_value.__truediv__.return_value
                mock_ht_resource.is_file.return_value = True
                mock_ht_resource.read_bytes.return_value = b"fake ht binary"

                # Mock tempfile creation
                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    mock_temp.return_value.__enter__.return_value.name = "/tmp/ht_test"

                    # Mock os.chmod
                    with patch("os.chmod"):
                        result = get_ht_binary()
                        assert result == "/tmp/ht_test"
                        assert "Using bundled ht binary" in caplog.text

    def test_env_var_overrides_bundled(self, monkeypatch, caplog):
        """Test that HTUTIL_HT_BIN overrides bundled ht when both exist."""
        # Set logging level to capture INFO messages
        with caplog.at_level("INFO", logger="htutil.ht"):
            # Create a temporary executable file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(b"#!/bin/sh\necho 'custom ht'\n")
                tmp_path = tmp.name

            # Make it executable
            os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)

            # Set the environment variable
            monkeypatch.setenv("HTUTIL_HT_BIN", tmp_path)

            try:
                # Mock the bundled ht to also exist
                with patch("pathlib.Path.exists") as mock_exists:

                    def exists_side_effect(path):
                        if "_bundled" in str(path):
                            return True
                        return os.path.exists(path)

                    mock_exists.side_effect = exists_side_effect

                    with patch("pathlib.Path.is_file", return_value=True):
                        result = get_ht_binary()
                        assert result == tmp_path
                        assert (
                            "Using user-specified ht binary from HTUTIL_HT_BIN"
                            in caplog.text
                        )
            finally:
                os.unlink(tmp_path)

    def test_empty_env_var_ignored(self, monkeypatch, caplog):
        """Test that empty HTUTIL_HT_BIN is ignored and falls back to system ht."""
        # Set logging level to capture WARNING messages
        with caplog.at_level("WARNING", logger="htutil.ht"):
            monkeypatch.setenv("HTUTIL_HT_BIN", "")

            # Mock importlib.resources to simulate no bundled ht
            with patch("importlib.resources.files") as mock_files:
                mock_files.side_effect = ImportError("No bundled resources")

                # Mock shutil.which to simulate system ht being available
                with patch("shutil.which") as mock_which:
                    mock_which.return_value = "/usr/bin/ht"

                    result = get_ht_binary()
                    assert result == "/usr/bin/ht"
                    assert (
                        "Using system ht binary from PATH: /usr/bin/ht" in caplog.text
                    )
                    assert "Version and compatibility are not guaranteed" in caplog.text

    def test_helpful_error_message_content(self, monkeypatch):
        """Test that helpful error message is shown when no ht binary is found anywhere."""
        # Ensure HTUTIL_HT_BIN is not set
        monkeypatch.delenv("HTUTIL_HT_BIN", raising=False)

        # Mock importlib.resources to simulate no bundled ht
        with patch("importlib.resources.files") as mock_files:
            mock_files.side_effect = ImportError("No bundled resources")

            # Mock shutil.which to simulate no system ht available
            with patch("shutil.which") as mock_which:
                mock_which.return_value = None

                with pytest.raises(RuntimeError) as exc_info:
                    get_ht_binary()

                error_msg = str(exc_info.value)
                # Check that helpful error message parts are present
                expected_parts = [
                    "Could not find ht binary",
                    "Install htutil from a wheel distribution",
                    "Install the 'ht' tool separately",
                    "Set HTUTIL_HT_BIN environment variable",
                    "https://github.com/andyk/ht",
                ]
                for part in expected_parts:
                    assert part in error_msg, f"Missing expected part: {part}"


class TestHTBinaryIntegration:
    """Integration tests for ht binary resolution in actual htutil usage."""

    @pytest.mark.skipif(
        not Path("src/htutil/ht.py").exists(),
        reason="ht.py not found - run from project root",
    )
    def test_patched_ht_py_imports(self):
        """Test that the patched ht.py can be imported successfully."""
        # This test assumes the patch has been applied
        # In a real scenario, you might want to apply the patch in a fixture
        pass
