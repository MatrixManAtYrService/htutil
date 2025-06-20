# ht

[ht](https://github.com/andyk/ht) lets you run subprocesses which are connected to a headless terminal.

To understand why this is useful, consider the vim startup screen:
```
~                       VIM - Vi IMproved
~                       version 9.0.2136
~                   by Bram Moolenaar et al.
~          Vim is open source and freely distributable
~
~                 Help poor children in Uganda!
````

It looks like a string in your terminal, so it might be tempting to treat it like a string in code:

```
import subprocess
vimproc = subprocess.Popen(["vim"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = vimproc.communicate()
assert stdout.lines[0][1:].strip() == "Sponsor Vim development!"
```

Or maybe like this:

```
❯ vim | grep IMproved
Vim: Warning: Output is not to a terminal
```

Vim is warning us of our first mistake, which was assuming that vim is writing to stdout (it's writing to /dev/tty).
But even tricker: it's not writing line-by-line but rather using ANSI escape codes to control the output.
If you captured what vim is writing to /dev/tty you'd see something like this:

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;32HHelp poor children in Uganda!
```

Working with `vim`'s actual output means working in a different world than what you actually see in your terminal.

[ht](https://github.com/andyk/ht) simplifies this by connecting the subprocess (`vim` in this case) to a fake terminal.
It lets you see how the output is rendered, rather than working with the output prior to rendering.
This simplifies testing significantly.

# htutil

`htutil` provides an alternative to the `ht` CLI and a python library, both which wrap [a fork of ht](https://github.com/MatrixManAtYrService/ht).


### CLI

Working with `ht` at the command line is a bit like having a chat session with the headless terminal.
Ask it to send keystrokes or to take snapshots by writing JSON objects to stdin and the answers come back to you on stdout in the form of other JSON objects.

The `htutil` CLI is not interactive like this.
It aims to do everything in a single command:

1. start the process
2. send keys, take snapshots
3. stop the process
4. write the snapshots to stdout


```
❯ htutil --snapshot -- vim | grep IMproved
~               VIM - Vi IMproved
```

You can take multiple snapshots in a single go:

```
❯ uv run htutil --rows 5 --cols 20 \
  -k 'ihello,Escape' --snapshot \
  -k 'Vyp,Escape'    --snapshot \
  -k ':q!,Enter' \
  -- vim
hello
~
~
~

----
hello
hello
~
~

----
```

In case you're vim-curious:
`ihello,Escape` enters insert mode types "hello" and goes back to normal mode.
`Vyp,Escape` enters line-wise visual mode with the the current line selected, yanks it, and puts it (so now there are two hello lines), and then goes back to normal mode.

For more on `htutil` CLI usage, run `htutil --help` or see the [docs]() TODO: fix this link.

To understand which keys you can send, see [keys.py](src/htutil/keys.py).
Anything which is not identified as a key will be sent as individual characters.

### Python Library

You can also import `htutil` as a python library.
It functions mostly like `ht`, except you control it by calling python functions.

There's a context manager for handling cleanup...
```python
from htutil import Press, ht_process, run

with ht_process(vim_path, rows=20, cols=50) as proc:
    snapshot = proc.snapshot()
    # ht_process terminates vim and cleans up ht on context exit

improved_line = next(
    line for line in snapshot.text.split("\n") if "IMproved" in line
)
assert improved_line == "~               VIM - Vi IMproved                 "
```

...or you can tell the subprocess to exit just like you would if you were typing into a terminal.
```python
proc = run("vim", rows=20, cols=50)
snapshot = proc.snapshot()
improved_line = next(line for line in lines if "IMproved" in snapshot.text.split('\n'))
assert improved_line == "~               VIM - Vi IMproved                 "

proc.send_keys(":q!")
proc.send_keys(Press.ENTER)    # vim quits, but ht stays open in case you want to take another snapshot
proc.exit()                    # exit ht
```

For more on using `htutil` as a python library, see the [docs]() TODO: fix this link.

# Contributing
### Prose

If you're looking at something that is obviously a bug, and you have a fix for it that isn't too adventurous, please submit a PR.
Feedback of any other sort (bugs, feature requests, etc) can go in an issue.

### Code

#### With Nix

htutil uses an experimental consistency framework: [checkdef](https://github.com/MatrixManAtYrService/checkdef) that requires nix.
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
nix build .#htutil-wheel
```

#### Without Nix

`htutil` is set up for use with `uv`.

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
export HTUTIL_WHEEL_PATH=$(pwd)/dist/htutil-0.1.0-py3-none-any.whl

# Run release tests (requires multiple Python versions: 3.10, 3.11, 3.12)
uv run pytest release_tests/ -v -s

# Or run specific test classes
uv run pytest release_tests/test_release.py::TestNixPython -v -s
uv run pytest release_tests/test_release.py::TestNixPythonConsistency -v -s
```

The release tests verify that:
- The wheel installs correctly across Python versions
- CLI commands work as expected
- Python API imports and functions properly
- Terminal sizing and text wrapping work correctly
- Results are consistent across Python versions

**Note**: Release tests require Python 3.10, 3.11, and 3.12 to be available on your system. You can install multiple Python versions using [pyenv](https://github.com/pyenv/pyenv) or your system package manager.
