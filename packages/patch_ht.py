#!/usr/bin/env python3
"""
Standalone script to patch ht.py to support HTUTIL_HT_BIN environment variable
"""

import sys
import re


def patch_ht_py(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Check if already patched
    if "get_ht_binary" in content:
        print("File already patched")
        return

    # Add the get_ht_binary function
    get_ht_binary_func = '''
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

'''

    # Find where to insert the function (after imports)
    lines = content.split("\n")
    import_section_end = 0

    for i, line in enumerate(lines):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            continue
        # If we find a non-import line, we've found the end of imports
        if (
            line.strip()
            and not line.startswith("import")
            and not line.startswith("from")
        ):
            import_section_end = i
            break

    # Insert the function after imports
    lines.insert(import_section_end, get_ht_binary_func)

    # Join lines back together
    content = "\n".join(lines)

    # Replace ht_cmd = ["ht", ...] with ht_cmd = [get_ht_binary(), ...]
    content = re.sub(r'ht_cmd = \["ht"', "ht_cmd = [get_ht_binary()", content)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Successfully patched {filepath}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: patch_ht.py <path_to_ht.py>")
        sys.exit(1)

    patch_ht_py(sys.argv[1])
