#!/usr/bin/env python3
import sys


def main():
    # foobar
    # Generate a number triangle pattern (used by tests)
    # 1
    # 22
    # 333
    # 4444
    # 55555
    for i in range(1, 6):
        sys.stdout.write(str(i) * i + "\n")


if __name__ == "__main__":
    main()
