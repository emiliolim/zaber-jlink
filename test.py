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
cap_block = {}  # Store CAP data waiting for ACC data

def try_create_entry(cap_data, acc_data):
    """Create entry if both CAP and ACC data are available"""
    if cap_data and acc_data:
        entry = cap_data | acc_data
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
                if not block.strip():  # Skip empty blocks
                    continue
                
                # Check if this block has CAP data
                cap_pattern = r"CAP(\d+): ([-+]?\d+(?:\.\d+)?)"
                cap_matches = re.findall(cap_pattern, block)
                
                if len(cap_matches) == 8:
                    # This is a CAP block
                    time_pattern = r"TIME: ([-+]?\d+(?:\.\d+)?)"
                    time_matches = re.findall(time_pattern, block)
                    if time_matches:
                        cap_entry = {f"CAP{cap}": float(val) for cap, val in cap_matches}
                        cap_entry["TIME"] = float(time_matches[0])
                        cap_block = cap_entry
                
                # Check if this block has ACC data
                accx_pattern = r"ACCX: ([-+]?\d+)"
                accy_pattern = r"ACCY: ([-+]?\d+)"
                accz_pattern = r"ACCZ: ([-+]?\d+)"
                
                accx_matches = re.findall(accx_pattern, block)
                accy_matches = re.findall(accy_pattern, block)
                accz_matches = re.findall(accz_pattern, block)
                
                if accx_matches and accy_matches and accz_matches:
                    # This is an ACC block
                    acc_entry = {
                        "ACCX": int(accx_matches[0]),
                        "ACCY": int(accy_matches[0]),
                        "ACCZ": int(accz_matches[0])
                    }
                    # Try to combine with stored CAP data
                    if cap_block:
                        entry = cap_block | acc_entry
                        values.append(entry)
                        print(entry)
                        cap_block = {}
            
            # Keep incomplete block in buffer
            buffer = blocks[-1]
        
        time.sleep(0.1)
except KeyboardInterrupt:
    jlink.rtt_stop()
    jlink.close()
