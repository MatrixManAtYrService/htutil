# htutil Release Tests

This directory contains release tests for the htutil package, particularly focused on testing the bundled version that will be distributed via PyPI.

## Overview

The release tests validate that:
- htutil installs correctly with the bundled ht binary
- The bundled ht binary is properly accessed using importlib.resources
- Terminal capture functionality works as expected
- The package works across different environments (via container tests)

## Test Structure

### Simple Release Tests (`test_simple_release.py`)
Basic tests that can run in a virtual environment without containers:
- Installation via pip
- Basic command execution
- Bundled binary detection

### Container Release Tests (`test_release_containers.py`)
More comprehensive tests using Docker/Podman containers:
- Tests across different Linux distributions (Debian, Alpine)
- Tests with different Python versions
- Tests various installation methods

### Nix Integration (`checks-release.nix`)
The Nix package runs basic smoke tests on the bundled htutil package to ensure:
- The CLI works (`htutil --help`)
- Terminal capture works (echo test)
- The bundled ht binary is being used

## Running the Tests

### Via Nix (Recommended)
```bash
nix build .#checks-release
```

### Manual Container Tests
```bash
# Requires Docker or Podman installed
python -m pytest release_tests/test_release_containers.py
```

### Simple Tests
```bash
python -m pytest release_tests/test_simple_release.py
```

## Implementation Notes

1. **Bundled Binary Access**: The htutil package uses `importlib.resources` to properly access the bundled ht binary, which works correctly even when the package is distributed as a wheel or installed in a zip-safe manner.

2. **Temporary Binary**: When using importlib.resources, the bundled ht binary is extracted to a temporary file at runtime, which is cleaned up on exit.

3. **Fallback Mechanism**: For development/editable installs, the code falls back to using `__file__` to locate the ht binary.

## Adding New Tests

When adding new tests:
1. For simple functionality tests, add them to `test_simple_release.py`
2. For environment-specific tests, add them to `test_release_containers.py`
3. For basic smoke tests in the Nix build, update `checks-release.nix`
