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
buffer = ""  # Accumulate data across reads

def parse_cap_block(block_text):
    """Parse a single complete CAP block (bounded by -----)"""
    cap_pattern = r"CAP(\d+): ([-+]?\d+(?:\.\d+)?)"
    cap_matches = re.findall(cap_pattern, block_text)

    time_pattern = r"TIME: ([-+]?\d+(?:\.\d+)?)"
    time_matches = re.findall(time_pattern, block_text)
    
    accx_pattern = r"ACCX: ([-+]?\d+)"
    accx_matches = re.findall(accx_pattern, block_text)
    
    accy_pattern = r"ACCY: ([-+]?\d+)"
    accy_matches = re.findall(accy_pattern, block_text)
    
    accz_pattern = r"ACCZ: ([-+]?\d+)"
    accz_matches = re.findall(accz_pattern, block_text)
    
    # Only create entry if we have all 8 CAP values AND TIME AND accelerometer data
    if len(cap_matches) == 8 and time_matches and accx_matches and accy_matches and accz_matches:
        cap_entry = {f"CAP{cap}": float(val) for cap, val in cap_matches}
        time_entry = {"TIME": float(time_matches[0])}
        acc_entry = {
            "ACCX": int(accx_matches[0]),
            "ACCY": int(accy_matches[0]),
            "ACCZ": int(accz_matches[0])
        }
        entry = cap_entry | time_entry | acc_entry
        values.append(entry)
        print(entry)
        return True
    return False

try:
    input("wait")
    while True:
        # Read from RTT terminal 0
        data = jlink.rtt_read(0, 1024)

        # Convert byte list to string
        text = bytes(data).decode('utf-8')
        if text:
            buffer += text
            
            # Split by block delimiter (-----)
            blocks = buffer.split('-----')
            
            # Process complete blocks (all but the last incomplete one)
            for block in blocks[:-1]:
                if block.strip():  # Skip empty blocks
                    parse_cap_block(block)
            
            # Keep incomplete block in buffer
            buffer = blocks[-1]
        
        time.sleep(0.1)
except KeyboardInterrupt:
    jlink.rtt_stop()
    jlink.close()
