# ht

[ht](https://github.com/andyk/ht) lets you run subprocesses which are connected to a headless terminal.

To understand why this is useful, consider this output, which you may have seen before:
```
~                       VIM - Vi IMproved
~                       version 9.0.2136
~                   by Bram Moolenaar et al.
~          Vim is open source and freely distributable
~                   Sponsor Vim development!
````

If you wanted to test this in python, it might be tempting to do something like this:

```
import subprocess
vimproc = subprocess.Popen(["vim"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = vimproc.communicate()
assert stdout.lines[-1].strip() == "Sponsor Vim development!"
```

There are problems with this approach:

1. vim is writing to /dev/tty, not stdout
2. it's not writing line-by-line but rather using ANSI escape codes to control the output

But if you captured vim's output you'd see something that won't work with the test above:

```
Vi IMproved[6;37Hversion 9.0.2136[7;33Hby Bram Moolenaar et al.[8;24HVim is open source and freely distributable[10;33HSponsor Vim development!
```

[ht](https://github.com/andyk/ht) solves this problem by connecting your subprocess (`vim` in this case) to a fake terminal.
It provides an interface that lets you how the fake terminal would render the output, instead of strings as `vim` provided them.
This simplifies testing significantly.

# htutil

`ht`'s interface makes sense if you want to use it to observe a persistent long-running session.
Something like this:

1. start ht (give it a command to run)
2. get a terminal snapshot
3. send ht some keystrokes to pass through to the headless terminal
4. get another snapshot
5. stop ht

For some cases that's great, but it's a little much if the subprocesses you're testing run to completion almost immediately.
