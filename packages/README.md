# htutil Package Outputs

This directory contains various Nix packages for htutil:

## Main Packages

### `htutil-dist-simple.nix`
The main distributable package for htutil. This creates a minimal package that:
- Contains the htutil Python application with all its dependencies
- Assumes `ht` is already available on the target system
- Can be built with: `nix build .#htutil-dist-simple`
- Can be copied to another machine and installed

Usage:
```bash
# Build the package
nix build .#htutil-dist-simple

# Copy the result to another machine
nix copy --to ssh://user@remote ./result

# On the remote machine (assuming ht is in PATH)
./result/bin/htutil -- echo "Hello"
```

### `htutil-package.nix`
A more complex package setup that provides multiple outputs:
- `default`: The basic htutil package
- `htutil`: Direct access to the Python package
- `htutil-dev`: Development environment with all dependencies

### Other Package Files

- `default.nix`: The original package definition with ht bundled
- `htutil.nix`: Legacy package that includes ht in PATH
- `htutil-dist.nix`: Builds htutil for multiple Python versions
- `htutil-pypi.nix`: Tools for building PyPI distributions (wheels/sdists)

## For PyPI Publishing

The project is configured with proper metadata in `pyproject.toml` for PyPI publishing:
- License: MIT
- Keywords and classifiers for discoverability
- Project URLs for documentation

To prepare for PyPI:
1. Update author information in pyproject.toml
2. Add a LICENSE file
3. Update the GitHub URLs
4. Build wheels/sdists using standard Python tools

## Notes

- All packages use uv2nix for dependency management
- The main distributable (`htutil-dist-simple`) assumes `ht` is available separately
- For a self-contained package with ht included, use the original `default.nix`
