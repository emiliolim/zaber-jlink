"""
Pretend this script is the EM test script
This will begin the subprocess of reading the vv sensor
"""

import subprocess
import time
import sys
import os
import signal
from zaber_cli import ZaberCLI
from futek_cli import FUTEKDeviceCLI

def run_test(save_path, run_number):
    cmd = [sys.executable, 'jlink.py', save_path, str(run_number)] # this is the command to run the test script. The second argument is the path where the data will be saved, and the third argument is the run number

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    proc = subprocess.Popen(
        cmd,
        creationflags=creationflags,
    )

    # Zaber port connection
    zaber = ZaberCLI()
    connection = zaber.connect(comport="COM3")

    # Futek Load Cell setup
    futek = FUTEKDeviceCLI()
    if connection == 0:
        print("Cannot Connect to Zaber comport")
        return 

    try:
        time.sleep(3) # this is to let the subprocess have time for init
        print("Main Script starting")
        while True:
            reading_force = futek.getNormalData()
            currentPosition = zaber.axis.get_position()
            #print(f"Force: {reading_force}, Position: {currentPosition}")
            #time.sleep(0.1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, stopping main loop")
    finally:
        print("Main Script stopping, cleaning up subprocess")
        if os.name == 'nt':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate() # ends subprocess

        # now wait for subprocess to cleanup
        try:
            proc.wait(timeout=10)
            print("Subprocess exited cleanly")
        except subprocess.TimeoutExpired:
            print("Subprocess took too long. Killing script")
            proc.kill()

run_test("CAP", 1)
            