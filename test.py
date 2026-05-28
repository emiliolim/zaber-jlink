"""
Use the pylink library to automatically read and parse
incoming data from the jlink connection

Current structure:
0) Main Zaber script starts THIS subprocess
1) Main function for this script takes in args from main Zaber script (save path) 
2) Opens Jlink connection 
3) Verifies that Jlink is recieving CAP data TODO: (Not done)
4) Begins data reading
5) Once test is finished in main script:
    5a) End data reading
    5b) Save data to CAP folder
    5c) Exit subprocess

Requires:
pylink
pylink-square
"""
import pylink
import time
import re
import signal
import sys
from pylink.enums import JLinkInterfaces

print("Subprocess starting")
jlink = pylink.JLink()
jlink.open()
jlink.set_tif(JLinkInterfaces.SWD)
jlink.connect('nRF52833_xxAA')

# Configure Real Time Transfer (RTT)
jlink.rtt_start()
values = []
buffer = ""  # Accumulate data across reads
current_entry = {}

TIME_PATTERN = re.compile(r"TIME:\s*([-+]?\d+(?:\.\d+)?)")
A_PATTERN = re.compile(r"A:\s*([-+]?\d+),([-+]?\d+),([-+]?\d+)")
C_PATTERN = re.compile(r"C:\s*([-+]?\d+),([-+]?\d+),([-+]?\d+),([-+]?\d+)")


def is_complete_entry(entry):
    if not entry:
        return False
    required_keys = ["TIME", "ACCX", "ACCY", "ACCZ"] + [f"CAP{i}" for i in range(1, 9)]
    return all(key in entry for key in required_keys)


def append_entry(entry):
    if is_complete_entry(entry):
        values.append(entry.copy())
        return True
    return False

def cleanup_and_exit(signum, frame):
    """
    Saves the values array into a excel file before exiting this subprocess
    """
    print("Running pre-exit tasks")
    try:
        jlink.rtt_stop()
    except Exception as exc:
        print(f"Failed to stop RTT cleanly: {exc}")
    try:
        jlink.close()
    except Exception as exc:
        print(f"Failed to close JLink cleanly: {exc}")
    append_entry(current_entry)
    print(values)
    print("Cleanup complete. Exiting")
    sys.exit(0)

# Register the handler 
signal.signal(signal.SIGTERM, cleanup_and_exit)
if hasattr(signal, 'SIGBREAK'):
    signal.signal(signal.SIGBREAK, cleanup_and_exit)

try:
    while True:
        # Read from RTT terminal 0
        data = jlink.rtt_read(0, 1024)

        # Convert byte list to string
        text = bytes(data).decode('utf-8')
        if text:
            buffer += text
            lines = buffer.splitlines(keepends=True)
            processed_lines = []

            # Keep the last partial line in the buffer
            if lines and not lines[-1].endswith("\n"):
                processed_lines = lines[:-1]
                buffer = lines[-1]
            else:
                processed_lines = lines
                buffer = ""

            for raw_line in processed_lines:
                line = raw_line.strip()
                if not line:
                    continue

                time_match = TIME_PATTERN.search(line)
                if time_match:
                    # finalize previous record if complete
                    if current_entry:
                        append_entry(current_entry)
                    current_entry = {
                        "TIME": float(time_match.group(1)),
                        "C_count": 0,
                    }
                    continue

                a_match = A_PATTERN.search(line)
                if a_match and current_entry:
                    current_entry["ACCX"] = int(a_match.group(1))
                    current_entry["ACCY"] = int(a_match.group(2))
                    current_entry["ACCZ"] = int(a_match.group(3))
                    continue

                c_match = C_PATTERN.search(line)
                if c_match and current_entry is not None:
                    count = current_entry.get("C_count", 0)
                    for idx, value in enumerate(c_match.groups(), start=1):
                        channel = count * 4 + idx
                        current_entry[f"CAP{channel}"] = int(value)
                    current_entry["C_count"] = count + 1
                    continue

        time.sleep(0.1)
except KeyboardInterrupt:
    cleanup_and_exit(None, None)
