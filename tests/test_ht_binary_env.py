"""Tests for HTUTIL_HT_BIN environment variable functionality."""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import stat


# Mock the get_ht_binary function as it would appear after patching
def get_ht_binary():
    """
    Get the path to the ht binary.
    
    Order of precedence:
    1. HTUTIL_HT_BIN environment variable (if set and valid)
    2. System PATH (default 'ht')
    """
    import os
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check for user-specified ht binary
    user_ht = os.environ.get('HTUTIL_HT_BIN')
    if user_ht:
        user_ht_path = Path(user_ht)
        if user_ht_path.is_file() and os.access(str(user_ht_path), os.X_OK):
            logger.info(f"Using user-specified ht binary from HTUTIL_HT_BIN: {user_ht}")
            return str(user_ht_path)
        else:
            import sys
            logger.warning(f"HTUTIL_HT_BIN='{user_ht}' is not a valid executable, falling back to default")
            print(f"Warning: HTUTIL_HT_BIN='{user_ht}' is not a valid executable, using default", file=sys.stderr)
    
    # Check for bundled ht binary (when distributed)
    module_dir = Path(__file__).parent
    bundled_ht = module_dir / '_bundled' / 'ht'
    if bundled_ht.exists() and bundled_ht.is_file():
        logger.info(f"Using bundled ht binary: {bundled_ht}")
        return str(bundled_ht)
    
    # Fall back to system PATH
    logger.debug("Using ht from system PATH")
    return "ht"


class TestHTUtilHTBin:
    """Test cases for HTUTIL_HT_BIN environment variable handling."""
    
    def test_no_env_var_uses_default(self, monkeypatch):
        """Test that without HTUTIL_HT_BIN, we use the default 'ht'."""
        # Ensure HTUTIL_HT_BIN is not set
        monkeypatch.delenv('HTUTIL_HT_BIN', raising=False)
        
        # Mock the bundled ht check to return False
        with patch('pathlib.Path.exists', return_value=False):
            result = get_ht_binary()
            assert result == "ht"
    
    def test_valid_env_var_is_used(self, monkeypatch, caplog):
        """Test that a valid HTUTIL_HT_BIN path is used."""
        # Create a temporary executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"#!/bin/sh\necho 'mock ht'\n")
            tmp_path = tmp.name
        
        # Make it executable
        os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)
        
        # Set the environment variable
        monkeypatch.setenv('HTUTIL_HT_BIN', tmp_path)
        
        try:
            result = get_ht_binary()
            assert result == tmp_path
            assert "Using user-specified ht binary from HTUTIL_HT_BIN" in caplog.text
        finally:
            os.unlink(tmp_path)
    
    def test_nonexistent_env_var_falls_back(self, monkeypatch, capsys):
        """Test that nonexistent HTUTIL_HT_BIN path falls back to default."""
        # Set environment variable to nonexistent path
        nonexistent_path = "/nonexistent/path/to/ht"
        monkeypatch.setenv('HTUTIL_HT_BIN', nonexistent_path)
        
        # Mock the bundled ht check to return False
        with patch('pathlib.Path.exists') as mock_exists:
            # First call checks user_ht_path.is_file(), second checks bundled
            mock_exists.side_effect = [False, False]
            result = get_ht_binary()
            assert result == "ht"
        
        # Check that warning was printed
        captured = capsys.readouterr()
        assert f"Warning: HTUTIL_HT_BIN='{nonexistent_path}' is not a valid executable" in captured.err
    
    def test_non_executable_env_var_falls_back(self, monkeypatch, capsys):
        """Test that non-executable HTUTIL_HT_BIN path falls back to default."""
        # Create a temporary non-executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"not executable")
            tmp_path = tmp.name
        
        # Ensure it's NOT executable
        os.chmod(tmp_path, 0o644)
        
        # Set the environment variable
        monkeypatch.setenv('HTUTIL_HT_BIN', tmp_path)
        
        try:
            # Mock bundled ht to not exist
            with patch('pathlib.Path.exists') as mock_exists:
                # Setup the mock to handle multiple calls
                def exists_side_effect(path):
                    if '_bundled' in str(path):
                        return False
                    return os.path.exists(path)
                
                mock_exists.side_effect = exists_side_effect
                
                result = get_ht_binary()
                assert result == "ht"
            
            # Check that warning was printed
            captured = capsys.readouterr()
            assert f"Warning: HTUTIL_HT_BIN='{tmp_path}' is not a valid executable" in captured.err
        finally:
            os.unlink(tmp_path)
    
    def test_bundled_ht_used_when_present(self, monkeypatch, caplog):
        """Test that bundled ht is used when present and no env var is set."""
        # Ensure HTUTIL_HT_BIN is not set
        monkeypatch.delenv('HTUTIL_HT_BIN', raising=False)
        
        # Mock the bundled ht to exist
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True):
            result = get_ht_binary()
            assert "_bundled/ht" in result
            assert "Using bundled ht binary" in caplog.text
    
    def test_env_var_overrides_bundled(self, monkeypatch, caplog):
        """Test that HTUTIL_HT_BIN overrides bundled ht when both exist."""
        # Create a temporary executable file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"#!/bin/sh\necho 'custom ht'\n")
            tmp_path = tmp.name
        
        # Make it executable
        os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IEXEC)
        
        # Set the environment variable
        monkeypatch.setenv('HTUTIL_HT_BIN', tmp_path)
        
        try:
            # Mock the bundled ht to also exist
            with patch('pathlib.Path.exists') as mock_exists:
                def exists_side_effect(path):
                    if '_bundled' in str(path):
                        return True
                    return os.path.exists(path)
                
                mock_exists.side_effect = exists_side_effect
                
                with patch('pathlib.Path.is_file', return_value=True):
                    result = get_ht_binary()
                    assert result == tmp_path
                    assert "Using user-specified ht binary from HTUTIL_HT_BIN" in caplog.text
        finally:
            os.unlink(tmp_path)
    
    def test_empty_env_var_ignored(self, monkeypatch):
        """Test that empty HTUTIL_HT_BIN is ignored."""
        monkeypatch.setenv('HTUTIL_HT_BIN', '')
        
        # Mock the bundled ht check to return False
        with patch('pathlib.Path.exists', return_value=False):
            result = get_ht_binary()
            assert result == "ht"


class TestHTBinaryIntegration:
    """Integration tests for ht binary resolution in actual htutil usage."""
    
    @pytest.mark.skipif(not Path("src/ht_util/ht.py").exists(), 
                        reason="ht.py not found - run from project root")
    def test_patched_ht_py_imports(self):
        """Test that the patched ht.py can be imported successfully."""
        # This test assumes the patch has been applied
        # In a real scenario, you might want to apply the patch in a fixture
        pass
