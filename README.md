# htutil

htutil is a tool for capturing how a terminal application will appear at some time.
It handles the ANSI control sequences and gives you a human-friendly string instead.

```
❯ htutil --snapshot -- vim | grep IMproved
~               VIM - Vi IMproved
```
It wraps [a lightly modified version of `ht`](https://github.com/MatrixManAtYrService/ht).

You can run `htutil` at the command line, or you can use python to `import htuil`.

## Headless Terminal (`ht`)

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

```python
import subprocess
vimproc = subprocess.Popen(["vim"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = vimproc.communicate()
assert stdout.lines[0][1:].strip() == "VIM - Vi IMproved"
```

Or maybe like this:

```bash
❯ vim | grep IMproved
Vim: Warning: Output is not to a terminal
```

Vim is warning us of our first mistake, which was assuming that vim is writing to stdout (it's writing to `/dev/tty`).

But the trickier problem is that it's not writing line-by-line but rather using ANSI escape codes to control the output.
If you captured what vim is writing you'd see something like this:

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;32HHelp poor children in Uganda!
```

`[6;37H` here means "row 6 column 37".
These numbers would be different if my terminal had been a different width when I captured that string.
This makes working with `vim`'s actual output quite challenging.

[ht](https://github.com/andyk/ht) can give you snapshots of the headless terminal so you don't have to deal with the ANSI codes.

## htutil CLI

Working with `ht` is a bit like having a chat session with a terminal.
You make requests by writing JSON to stdin, requests like "press key" or "take snapshot".
You get responses as more JSON from stdout.

The `htutil` CLI is not interactive like this.
It aims to do everything in a single command:

1. start the process
2. send keys, take snapshots
3. stop the process
4. write the snapshots to stdout

You can take multiple snapshots in a single go:

```
❯ htutil --rows 5 --cols 20 \
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

- `ihello,Escape` enters insert mode types "hello" and goes back to normal mode.
- `Vyp,Escape` enters line-wise visual mode with the the current line selected, yanks it, and puts it (so now there are two hello lines), and then goes back to normal mode.

For more on `htutil` CLI usage, run `htutil --help` or see the [docs]() TODO: fix this link.

To understand which keys you can send, see [keys.py](src/htutil/keys.py).
Anything which is not identified as a key will be sent as individual characters.

## htutil Python Library

As a python library, `htuitl` functions mostly like `ht`.
Unlike the `htutil` cli, it doesn't require you to do everything in one step.

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to this project.
