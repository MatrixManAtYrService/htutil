"""
Simple test using the ht_util module to make assertions about terminal output.
"""
import sys
import os
import time
import pytest
import tempfile
import ht_util

# The hello_world.py content as a string
HELLO_WORLD_SCRIPT = """
from time import sleep
print("hello")
input()
print("world")
sleep(2)
print("goodbye")
"""


@pytest.fixture
def hello_world_script():
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as tmp:
        tmp.write(HELLO_WORLD_SCRIPT.encode('utf-8'))
        tmp_path = tmp.name
    
    yield tmp_path
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

def test_hello_world_with_scrolling(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    proc = ht_util.run(cmd, rows=3, cols=8)
    
    time.sleep(0.1)
    assert ht_util.snapshot(proc) == (
        "hello   \n"
        "        \n"
        "        "
    )

    proc.send_keys("Enter")
    time.sleep(0.1)
    assert ht_util.snapshot(proc) == (
        "        \n"
        "world   \n"
        "        "
    )


def test_hello_world_after_exit(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    ht = ht_util.run(cmd, rows=4, cols=8, no_exit=True)
    ht.send_keys("Enter")
    ht.wait()
    assert ht_util.snapshot(ht) == (
        "hello   \n"
        "world   \n"
        "goodbye \n"
        "        "
    )

def test_outputs(hello_world_script):
    cmd = f"{sys.executable} {hello_world_script}"
    ht = ht_util.run(cmd, rows=4, cols=8, no_exit=True)
    ht.send_keys("Enter")
    ht.wait()
    assert ht_util.output[0] == {"data":{"seq":"\r\n"},"type":"output"}
    assert ht_util.output[1] == {"data":{"seq":"hello\r\nworld\r\n"},"type":"output"}
    assert ht_util.output[2] == {"data":{"seq":"goodbye\r\n"},"type":"output"}
