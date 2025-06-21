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

`[6;37H` here means "row 6 column 37".
These numbers would be different if my terminal had been a different width when I captured that string.
This makes working with `vim`'s actual output quite different than working with the strings that you actually see on your screen.

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

- `ihello,Escape` enters insert mode types "hello" and goes back to normal mode.
- `Vyp,Escape` enters line-wise visual mode with the the current line selected, yanks it, and puts it (so now there are two hello lines), and then goes back to normal mode.

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to this project.
