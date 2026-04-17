"""
Use the pylink library to automatically read and parse
incoming data from the jlink connection

Requires:
pylink
pylink-square
"""
import pylink
import time
import re
from pylink.enums import JLinkInterfaces

jlink = pylink.JLink()
jlink.open()
jlink.set_tif(JLinkInterfaces.SWD)
jlink.connect('nRF52833_xxAA')

# Configure Real Time Transfer (RTT)
jlink.rtt_start()
values = []
def parse_and_store(raw_str):
    cap_pattern = r"CAP(\d+): ([-+]?\d+(?:\.\d+)?)"
    cap_matches = re.findall(cap_pattern, raw_str)

    time_pattern = r"TIME: ([-+]?\d+(?:\.\d+)?)"
    time_matches = re.findall(time_pattern, raw_str)
    if cap_matches:
        cap_entry = {f"CAP{cap}": float(val) for cap, val in cap_matches}
        time_entry = {f"TIME": float(val) for val in time_matches}
        entry = cap_entry | time_entry
        values.append(entry)
        print(entry)

try:
    input("wait")
    while True:
        # Read from RTT terminal 0
        data = jlink.rtt_read(0, 1024)

        # Convert byte list to string
        text = bytes(data).decode('utf-8')
        if data:
            print(text)
            parse_and_store(text)
        time.sleep(0.1)
except KeyboardInterrupt:
    jlink.rtt_stop()
    jlink.close()
