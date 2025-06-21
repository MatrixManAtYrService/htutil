# htty

![CI](https://github.com/MatrixManAtYrService/htty/workflows/CI/badge.svg)

htty programatically captures the appearance of a terminal application.

!["htty taking a snapshot of a vim session"](improved.png)

It's a wrapper around [a lightly modified version of `ht`](https://github.com/MatrixManAtYrService/ht).
Which handles ANSI control sequences and gives you a friendly string instead.


You can run `htty` at the command line, or you can use python to `import htuil`.

## Headless Terminal (`ht`)

[ht](https://github.com/andyk/ht) connects a subprocess to a headless terminal.
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

!["vim showing an error if you try to pipe its output to grep"](error.png)

But these approaches won't work.
If you captured vim's output you'd see that it looks quite different than what you see in your terminal:

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;32HHelp poor children in Uganda!
```

[ht](https://github.com/andyk/ht) reads raw output like you see above and renders it as if a terminal was attached.
`htty` provides a convenient way to use `ht`

## htty CLI

Working with `ht` is a bit like having a chat session with a terminal.
You make requests by writing JSON to stdin, requests like "press escape" or "take snapshot".
You get responses as more JSON from stdout.

The `htty` CLI is not interactive like this.
It aims to do everything in a single command:

1. start the process
2. send keys, take snapshots
3. stop the process
4. write the snapshots to stdout

You can take multiple snapshots in a single go:

!["htty taking several snapshots of a vim session at different times"](hellohello.png)

In case you're vim-curious:

- `ihello,Escape` enters insert mode types "hello" and goes back to normal mode.
- `Vyp,Escape` enters line-wise visual mode with the the current line selected, yanks it, and puts it (so now there are two hello lines), and then goes back to normal mode.

For more on `htty` CLI usage, run `htty --help` or see the [docs]() TODO: fix this link.

To understand which keys you can send, see [keys.py](src/htty/keys.py).
Anything which is not identified as a key will be sent as individual characters.

## htty Python Library

As a python library, `htty` functions mostly like `ht`.

```python
from htty import Press, ht_process, run

with ht_process("vim", rows=20, cols=50) as proc:
    snapshot = proc.snapshot()
    # ht_process terminates vim and cleans up ht on context exit

improved_line = next(
    line for line in snapshot.text.split("\n") if "IMproved" in line
)
assert improved_line == "~               VIM - Vi IMproved                 "
```

Alternative usage:
```python
proc = run("vim", rows=20, cols=50)
snapshot = proc.snapshot()
improved_line = next(line for line in lines if "IMproved" in snapshot.text.split('\n'))
assert improved_line == "~               VIM - Vi IMproved                 "

proc.send_keys(":q!")
proc.send_keys(Press.ENTER)    # vim quits, but ht stays open in case you want to take another snapshot
proc.exit()                    # exit ht
```

For more on using `htty` as a python library, see the [docs]() TODO: fix this link.

# Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to this project.
