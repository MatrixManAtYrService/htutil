# Contributing

## Prose

If you're looking at something that is obviously a bug, and you have a fix for it that isn't too adventurous, please submit a PR.
Feedback of any other sort (bugs, feature requests, etc) can go in an issue.

## Code

### With Nix

htty uses an experimental consistency framework: [checkdef](https://github.com/MatrixManAtYrService/checkdef) that requires nix.
Commands to try:

```
nix run .#checklist-fast    # linters and such
nix run .#checklist-full    # the fast checks, plus unit tests
nix run .#checklist-release # the full checks, plus release tests
```

These also support verbose mode `nix run .#checklist-release -- -v`

The nix devshell is configured with `uv` for easy access to the python environment, so you can run commands like this:
```
uv run pytest ./tests
```

If you're not already in an interactive nix devshell (looking at you, AI agents), consider this instead:
```
nix develop --command uv run pytest ./tests
```

To ensure that my editor has access to the declared environment (python and otherwise), I like to run it in the project devshell:
```
nix develop --command uv run hx                             # feeling focused
nix develop --command uv run open /Applications/Cursor.app  # feeling reckless
```

You can access the wheel for your system architecture (with bundled `ht`) like so:

```
nix build .#htty-wheel
```

### Without Nix

`htty` is set up for use with `uv`.

```
# Create a virtual environment and install dependencies
uv sync --dev

# Run the unit tests
uv run pytest tests
```

**Note**: [Some tests](tests/test_ht_util_cli.py) require `vim` to be installed (it is used as a test target).
Nix is the best way to inject the version of vim that those tests depend on, but you can probably also get away with just ignoring them.

To build a wheel that includes the `ht` binary, use the provided Makefile:

```bash
# be sure cargo is installed first
make wheel
```

Once you have a wheel, you can run the release tests:

```bash
# Set the wheel path for release tests
export HTTY_WHEEL_PATH=$(pwd)/dist/htty-0.1.0-py3-none-any.whl

# Run release tests (requires multiple Python versions: 3.10, 3.11, 3.12)
uv run pytest test_release/ -v -s

# Or run specific test classes
uv run pytest test_release/test_release.py::TestNixPython -v -s
uv run pytest test_release/test_release.py::TestNixPythonConsistency -v -s
```

The release tests verify that:
- The wheel installs correctly across Python versions
- CLI commands work as expected
- Python API imports and functions properly
- Terminal sizing and text wrapping work correctly
- Results are consistent across Python versions

**Note**: Release tests require Python 3.10, 3.11, and 3.12 to be available on your system. You can install multiple Python versions using [pyenv](https://github.com/pyenv/pyenv) or your system package manager.