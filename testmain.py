"""
Pretend this script is the EM test script
This will begin the subprocess of reading the vv sensor
"""

import subprocess
import time
import sys
import os
import signal

def run_test(save_path, run_number):
    cmd = [sys.executable, 'test2.py', save_path, str(run_number)] # this is the command to run the test script. The second argument is the path where the data will be saved, and the third argument is the run number

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    proc = subprocess.Popen(
        cmd,
        creationflags=creationflags,
    )

    try:
        time.sleep(3) # this is to let the subprocess have time for init
    finally:
        print("Main Script starting")
        while True:
            i = input("-1 to exit")
            if i == "-1":
                break
        if os.name == 'nt':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate() # ends subprocess

        # now wait for subprocess to cleanup
        try:
            proc.wait(timeout=10)
            print("Subprocess exited cleanly")
        except subprocess.TimeoutExpired:
            print("Subprocess took to long. Killing script")
            proc.kill()

run_test("CAP", 1)
            