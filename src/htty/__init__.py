import os
import shutil
import warnings

from htty.ht import (
    HTBinary,
    SnapshotResult,
    ht_binary,
    ht_process,
    run,
)
from htty.keys import (
    KeyInput,
    Press,
    key_to_string,
)

__all__ = [
    "HTBinary",
    "SnapshotResult",
    "ht_binary",
    "ht_process",
    "run",
    "KeyInput",
    "Press",
    "key_to_string",
]


def _check_installation_type_and_warn() -> None:
    """
    Check if this is a source installation without bundled ht binary and warn user.

    This helps users who install from sdist on unsupported platforms understand
    why htty might not work and what they need to do.
    """
    # Skip warning if user has explicitly set HTTY_HT_BIN
    if os.environ.get("HTTY_HT_BIN"):
        return

    # Check if we have a bundled binary (wheel installation)
    try:
        from importlib import resources as impresources

        from . import _bundled

        bundled_files = impresources.files(_bundled)
        ht_resource = bundled_files / "ht"

        if ht_resource.is_file():
            # We have a bundled binary, this is a wheel installation - no warning needed
            return
    except (ImportError, FileNotFoundError, AttributeError):
        # No bundled binary found - this is likely a source installation
        pass

    # Check if ht is available in system PATH
    if shutil.which("ht"):
        # System ht available - user might be okay, but show a gentle warning
        warnings.warn(
            "htty: Using system 'ht' binary from PATH. "
            "For best compatibility, consider installing a wheel distribution "
            "which bundles the correct ht version. "
            "See: https://github.com/MatrixManAtYrService/htty#installation",
            UserWarning,
            stacklevel=2,
        )
        return

    # No bundled binary and no system ht - this will likely fail
    import platform

    arch = platform.machine()
    system = platform.system()

    warnings.warn(
        f"htty installation warning: No 'ht' binary found for {system} {arch}.\n\n"
        "You installed htty from source, but htty requires the 'ht' binary to function.\n"
        "This installation will not work until you:\n\n"
        "1. Install ht separately: https://github.com/andyk/ht\n"
        "   Then ensure it's in your PATH\n"
        "2. Set HTTY_HT_BIN environment variable:\n"
        "   export HTTY_HT_BIN=/path/to/ht\n"
        "3. Or install a wheel distribution with bundled ht:\n"
        "   pip install --force-reinstall --no-deps htty\n\n"
        "Supported platforms with pre-built wheels:\n"
        "• Linux: x86_64, aarch64  • macOS: x86_64, arm64\n\n"
        "For help: https://github.com/MatrixManAtYrService/htty/issues",
        UserWarning,
        stacklevel=2,
    )


# Show installation warning on import (only for problematic installations)
_check_installation_type_and_warn()
