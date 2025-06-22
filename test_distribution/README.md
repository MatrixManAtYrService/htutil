# Distribution Tests

This directory contains tests that validate htty's distribution and installation experience for end users. These tests are designed to catch issues that might not be apparent in development but would affect users installing htty from PyPI.

## Test Types

### 1. Simple Isolation Tests (`test_simple_isolation.py`)

These tests use Python virtual environments to simulate clean installation scenarios:

- **Wheel Installation**: Tests installing the wheel package and verifying:
  - Successful installation
  - Console scripts (`htty`, `htty-ht`) are available
  - Import works without warnings (bundled binary)
  
- **Sdist Installation**: Tests installing from source distribution and verifying:
  - Successful installation (with build dependencies)
  - Console scripts are available
  - Import works with appropriate warnings (no bundled binary)
  
- **Consistency**: Verifies that wheel and sdist install the same console scripts

**Runs in**: Nix environment (part of `nix run .#checklist-dist`)

### 2. Installation Warning Tests (`test_installation_warnings.py`)

Tests the warning system that helps users understand what to expect:

- PyPI installation simulation with clean virtual environments
- Console script availability verification
- Warning message validation for different scenarios

**Runs in**: Nix environment (part of `nix run .#checklist-dist`)

### 3. Docker Isolation Tests (`test_docker_isolation.py`)

**Complete isolation from Nix** using Docker containers to simulate real user environments:

- **Wheel Container**: Ubuntu 22.04 with Python, tests wheel installation
- **Sdist Container**: Ubuntu 22.04 with Python + build tools, tests sdist installation
- Tests installation, console scripts, imports, and warnings in truly clean environments

**Runs manually**: Use `python test_distribution/run_docker_tests.py` when Docker is available

## Running Tests

### All Distribution Tests (Simple + Warnings)
```bash
nix run .#checklist-dist
```

### Docker Tests (Manual)
```bash
# Build artifacts first
nix build .#htty-wheel .#htty-sdist

# Run Docker tests (requires Docker/Podman)
python test_distribution/run_docker_tests.py
```

### Individual Test Files
```bash
# Simple isolation tests
python -m pytest test_distribution/test_simple_isolation.py -v

# Installation warning tests  
python -m pytest test_distribution/test_installation_warnings.py -v

# Docker tests (requires Docker and artifacts)
CONTAINER_TOOL=docker HTTY_WHEEL_PATH=result-wheel/htty-*.whl HTTY_SDIST_PATH=result-sdist/htty-*.tar.gz \
python -m pytest test_distribution/test_docker_isolation.py -v
```

## What These Tests Catch

1. **Missing console scripts**: Ensures `htty` and `htty-ht` commands are available after installation
2. **Import issues**: Catches problems with module imports or missing dependencies
3. **Warning system**: Verifies users get helpful guidance when `ht` binary is missing
4. **Installation failures**: Detects issues with wheel/sdist packaging
5. **Cross-platform consistency**: Ensures wheel and sdist behave the same way
6. **Real user experience**: Docker tests simulate exactly what users will experience

## Design Philosophy

These tests follow the principle: **"Test what users actually experience"**

- **No Nix dependencies** in the test environments (especially Docker tests)
- **Real PyPI-style installation** using pip in clean virtual environments
- **Actual artifacts** built by the Nix build system, not development code
- **Multiple installation methods** (wheel vs sdist) to cover different user scenarios
- **Helpful error messages** when things go wrong, just like users would see

The goal is to catch distribution issues **before** they reach users, ensuring that `pip install htty` works reliably across different platforms and Python environments. 