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
from pathlib import Path
import xlsxwriter
from pylink.enums import JLinkInterfaces


def try_create_entry(cap_data, acc_data, values):
    """Create entry if both CAP and ACC data are available"""
    if cap_data and acc_data:
        entry = cap_data | acc_data
        values.append(entry)
        #print(entry)
        return True
    return False


def save_data(values, savepath, run):
    """
    Saves the values array into a excel file before exiting this subprocess
    values :: array of dictionaries
    savepath :: string
    run :: int
    """
    path = Path(savepath)
    filename = f"run {run}.xlsx"
    path = path / filename 
    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet(str(run))

    worksheet.write('A1', 'Index')
    worksheet.write('B1', 'CAP1')
    worksheet.write('C1', 'CAP2')
    worksheet.write('D1', 'CAP3')
    worksheet.write('E1', 'CAP4')
    worksheet.write('F1', 'CAP5')
    worksheet.write('G1', 'CAP6')
    worksheet.write('H1', 'CAP7')
    worksheet.write('I1', 'CAP8')
    worksheet.write('J1', 'TIME')
    worksheet.write('K1', 'ACCX')
    worksheet.write('L1', 'ACCY')
    worksheet.write('M1', 'ACCZ')
    for i, entry in enumerate(values):
        worksheet.write(i + 1, 0, i)  # Index
        worksheet.write(i + 1, 1, entry.get('CAP1', ''))  # CAP1
        worksheet.write(i + 1, 2, entry.get('CAP2', ''))  # CAP2
        worksheet.write(i + 1, 3, entry.get('CAP3', ''))  # CAP3
        worksheet.write(i + 1, 4, entry.get('CAP4', ''))  # CAP4
        worksheet.write(i + 1, 5, entry.get('CAP5', ''))  # CAP5
        worksheet.write(i + 1, 6, entry.get('CAP6', ''))  # CAP6
        worksheet.write(i + 1, 7, entry.get('CAP7', ''))  # CAP7
        worksheet.write(i + 1, 8, entry.get('CAP8', ''))  # CAP8
        worksheet.write(i + 1, 9, entry.get('TIME', ''))   # TIME
        worksheet.write(i + 1, 10, entry.get('ACCX', '')) # ACCX
        worksheet.write(i + 1, 11, entry.get('ACCY', '')) # ACCY
        worksheet.write(i + 1, 12, entry.get('ACCZ', '')) # ACCZ
    workbook.close()

def main(savepath, run):
    """
    savepath:: string
    run:: int
    """
    print(f"Subprocess started. Saving data to: {savepath}")
    jlink = pylink.JLink()
    jlink.open()
    jlink.set_tif(JLinkInterfaces.SWD)
    jlink.connect('nRF52833_xxAA')

    # Configure Real Time Transfer (RTT)
    jlink.rtt_start()
    values = []
    buffer = ""  # Accumulate data across reads
    cap_block = {}  # Store CAP data waiting for ACC data

    def cleanup_and_exit(signum, frame):
        """
        Closes RTT link and saves values array
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
        save_data(values, savepath, run)
        print("Cleanup complete. Exiting")
        sys.exit(0)

    # Register the handlers
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
                            #print(entry)
                            cap_block = {}

                # Keep incomplete block in buffer
                buffer = blocks[-1]

            time.sleep(0.1)
    except KeyboardInterrupt:
        cleanup_and_exit(None, None)


if __name__ == "__main__":
    # Check if the argument was actually passed to avoid IndexErrors
    if len(sys.argv) > 2:
        path = sys.argv[1]
        run = int(sys.argv[2])
    else:
        path = "./"
        run = 0
        
    main(path, run)
