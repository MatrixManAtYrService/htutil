import os
import platform
import shutil
import warnings
from importlib import resources as impresources

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

from . import _bundled

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
        bundled_files = impresources.files(_bundled)
        ht_resource = bundled_files / "ht"

        if ht_resource.is_file():
            # We have a bundled binary, this is a wheel installation - no message needed
            return

    except FileNotFoundError:
        arch = platform.machine()
        system = platform.system()
        msg = (
            "htty requires a build of 'ht' from this fork: https://github.com/MatrixManAtYrService/ht "
            "Wheel distributions of htty bundle it, but source distributions do not. "
            f"You appear to have installed a source distribution, likely because no wheel is available "
            f"for {arch} {system}.\n"
            "If you'd like a wheel for your platform please open an issue: https://github.com/MatrixManAtYrService/htty/issues.\n"
            "Available wheels are listed here: https://pypi.org/project/htty/#files\n\n"
        )

        # Check if ht is available in system PATH
        ht_path = shutil.which("ht")
        if ht_path:
            msg += f"If {ht_path} is not from this fork, you may encounter issues. "
        else:
            msg += "`ht` is not in the PATH. To use htty, you'll need to build/install it separately. "

        msg += "To override the `ht` binary used by htty, set the `HTTY_HT_BIN`. \n\n"

        warnings.warn(
            msg,
            UserWarning,
            stacklevel=2,
        )


# Show installation warning on import (only for problematic installations)
_check_installation_type_and_warn()
