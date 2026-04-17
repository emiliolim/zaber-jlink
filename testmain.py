"""
Pretend this script is the EM test script
This will begin the subprocess of reading the vv sensor
"""

import subprocess
import time
import sys

def run_test():
    proc = subprocess.Popen([sys.executable, 'test.py'])

    try:
        time.sleep(3) # this is to let the subprocess have time for init
    finally:
        print("Main Script starting")
        while True:
            i = input("-1 to exit")
            if i == "-1":
                break
        proc.terminate() # ends subprocess

        # now wait for subprocess to cleanup
        try:
            proc.wait(timeout=5)
            print("Subprocess exited cleanly")
        except subprocess.TimeoutExpired:
            print("Subprocess took to long. Killing script")
            proc.kill()
run_test()
            