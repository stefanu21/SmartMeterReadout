import serial
import os
import signal
import sys
import time
import traceback
import argparse
import subprocess
import threading
from binascii import unhexlify
from datetime import datetime
from gurux_dlms.GXByteBuffer import GXByteBuffer
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from gurux_dlms.GXDLMSTranslator import GXDLMSTranslator
import lxml  # needs to be installed and imported for better performance with BeautifulSoup
from bs4 import BeautifulSoup

# -- CONFIGURATION BEGIN -- #

# SERIAL COMMUNICATION
COM_PORT = "/dev/ttyUSB0"
BAUDRATE = 2400
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE
BYTESIZE = serial.EIGHTBITS
TIMEOUT = 3  # As the meter sends data every 5s the timeout must be <5s

# SMART METER MESSAGE - SPECIFIC
FRAME_LENGTH = 376
# Message consists of 2 frames.
FRAME1_START_BYTE = b"\x68"
FRAME2_END_BYTE = b"\x16"
# AES key format, e.g. 48E2C...
# Default VNB_KEY - can be overridden via command line parameter
VNB_KEY = "<YOUR KEY>"
LOG_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.basename(__file__)[:-2]+"log"))
# LOG_FILE = ""  # if you don't want to log
PRINT_LOGS = True

# DATA LOGGING
DATA_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), "power_data.csv"))
ENABLE_DATA_LOGGING = True
LOGGING_INTERVAL = 1  # Log every N-th measurement (1 = every measurement, 2 = every 2nd, etc.)
                      # Smart meter sends data every ~5 seconds
                      # LOGGING_INTERVAL=1  -> ~5 sec  (720 entries/hour)
                      # LOGGING_INTERVAL=12 -> ~60 sec (60 entries/hour)
                      # LOGGING_INTERVAL=60 -> ~5 min  (12 entries/hour)

# -- CONFIGURATION END -- #

# OBIS = {
#     "0.0.1.0.0.255":  "Datum und Uhrzeit",
#     "0.0.96.1.0.255": "Zählernummer des Netzbetreibers",
#     "0.0.42.0.0.255": "COSEM logical device name",
#     "1.0.32.7.0.255": "Spannung L1",
#     "1.0.52.7.0.255": "Spannung L2",
#     "1.0.72.7.0.255": "Spannung L3",
#     "1.0.31.7.0.255": "Strom L1",
#     "1.0.51.7.0.255": "Strom L2",
#     "1.0.71.7.0.255": "Strom L3",
#     "1.0.1.7.0.255":  "Wirkleistung Bezug +P",
#     "1.0.2.7.0.255":  "Wirkleistung Lieferung -P",
#     "1.0.1.8.0.255":  "Wirkenergie Bezug +A (Wh)",
#     "1.0.2.8.0.255":  "Wirkenergie Lieferung -A (Wh)",
#     "1.0.3.8.0.255":  "Blindenergie Bezug +R (Wh)",
#     "1.0.4.8.0.255":  "Blindenergie Lieferung -R (Wh)",
# }
OBIS_DATE = "0.0.1.0.0.255"
OBIS = {
    "1.0.32.7.0.255": "VoltageL1",
    "1.0.52.7.0.255": "VoltageL2",
    "1.0.72.7.0.255": "VoltageL3",
    "1.0.31.7.0.255": "CurrentL1",
    "1.0.51.7.0.255": "CurrentL2",
    "1.0.71.7.0.255": "CurrentL3",
    "1.0.1.7.0.255":  "RealPowerIn",
    "1.0.2.7.0.255":  "RealPowerOut",
    "1.0.1.8.0.255":  "RealEnergyIn",
    "1.0.2.8.0.255":  "RealEnergyOut",
    "1.0.3.8.0.255":  "ReactiveEnergyIn",
    "1.0.4.8.0.255":  "ReactiveEnergyOut",
}
OBIS_UNUSED = {
    "0.0.96.1.0.255": "MeterID",
    "0.0.42.0.0.255": "MeterType",
}


def log(msg, error=False):
    global LOG_FILE
    if error:
        msg = "ERROR: " + msg
    if PRINT_LOGS:
        print(msg, file=sys.stderr if error else None)
    if LOG_FILE:
        msg = datetime.now().strftime("%Y-%m-%d %H:%M:%S - ") + str(os.getpid()) + ": " + msg
        with open(LOG_FILE, "a") as log_file:
            log_file.write("\n" + msg)


def log_power_data(timestamp, real_power_in, real_power_out, real_power_net, real_energy_in, real_energy_out):
    """Log power data to CSV file for later graphing. Appends to existing file."""
    global DATA_FILE, ENABLE_DATA_LOGGING
    if not ENABLE_DATA_LOGGING:
        return
    
    try:
        # Check if file exists and has content
        file_exists = os.path.isfile(DATA_FILE)
        write_header = False
        
        if not file_exists:
            write_header = True
        elif os.path.getsize(DATA_FILE) == 0:
            # File exists but is empty
            write_header = True
        
        # Open file in append mode (does not overwrite)
        with open(DATA_FILE, "a") as data_file:
            # Write header only if file is new or empty
            if write_header:
                data_file.write("timestamp,datetime,real_power_in,real_power_out,real_power_net,real_energy_in,real_energy_out\n")
            
            # Write data row
            dt_string = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            data_file.write(f"{timestamp},{dt_string},{real_power_in},{real_power_out},{real_power_net},{real_energy_in},{real_energy_out}\n")
    except Exception as e:
        log(f"Error writing power data: {str(e)}", True)


class SignalHandler:
    _shutdown = False
    _immediately = False

    def __init__(self, shutdown_immediately=False):
        self._immediately = shutdown_immediately
        signal.signal(signal.SIGINT, self._request_shutdown)
        signal.signal(signal.SIGTERM, self._request_shutdown)

    def _request_shutdown(self, *args):
        log('Request to shutdown received. Stopping...')
        self._shutdown = True
        if self._immediately:
            quit()

    def shutdown_requested(self):
        return self._shutdown


# Parse command line arguments
parser = argparse.ArgumentParser(description='Smart Meter Readout - DLMS/COSEM Protocol')
parser.add_argument('--key', type=str, help='AES decryption key (VNB_KEY) in hex format, e.g., 48E2C...')
parser.add_argument('--port', type=str, default=COM_PORT, help=f'Serial port (default: {COM_PORT})')
parser.add_argument('--gui', action='store_true', help='Start live GUI monitor in a separate window')
parser.add_argument('--gui-hours', type=float, default=1, help='Hours to display in GUI (default: 1)')
parser.add_argument('--log-interval', type=int, default=LOGGING_INTERVAL, 
                   help=f'Log every N-th measurement (default: {LOGGING_INTERVAL}). '
                        f'Smart meter sends ~every 5 sec. Examples: 1=5sec, 12=1min, 60=5min')
parser.add_argument('--clear-data', action='store_true',
                   help='Delete old data and start fresh (creates backup as power_data.csv.backup)')
args = parser.parse_args()

# Handle --clear-data option
if args.clear_data:
    if os.path.exists(DATA_FILE):
        backup_file = DATA_FILE + '.backup'
        log(f"Creating backup of old data: {backup_file}")
        try:
            import shutil
            shutil.copy2(DATA_FILE, backup_file)
            log(f"Backup saved to: {backup_file}")
        except Exception as e:
            log(f"Error creating backup: {str(e)}", True)
            sys.exit(1)
    
    # Create new empty file with header (don't delete - GUI might already be starting)
    try:
        with open(DATA_FILE, 'w') as f:
            f.write("timestamp,datetime,real_power_in,real_power_out,real_power_net,real_energy_in,real_energy_out\n")
        log("Old data cleared. Starting fresh with new file.")
    except Exception as e:
        log(f"Error creating new data file: {str(e)}", True)
        sys.exit(1)

# Override configuration from command line
if args.key:
    VNB_KEY = args.key
    log(f"Using VNB_KEY from command line parameter")
if args.port:
    COM_PORT = args.port
if args.log_interval:
    LOGGING_INTERVAL = args.log_interval
    log(f"Logging interval set to every {LOGGING_INTERVAL} measurement(s) (~{LOGGING_INTERVAL * 5} seconds)")
    COM_PORT = args.port

log("Start " + os.path.basename(__file__))
log(f"Using serial port: {COM_PORT}")
log(f"Using VNB_KEY: {VNB_KEY[:8]}... (first 8 chars shown)")

# Start GUI monitor if requested
gui_process = None
if args.gui:
    # Check if display is available
    if 'DISPLAY' not in os.environ and sys.platform.startswith('linux'):
        log("Warning: --gui option ignored - no DISPLAY environment variable found", True)
        log("GUI requires a graphical environment. Use plot_power_data.py for static plots instead.")
        log("Tip: If you have a desktop, you may need to install python3-tk: sudo apt-get install python3-tk")
    else:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            gui_script = os.path.join(script_dir, "live_monitor.py")
            
            if os.path.exists(gui_script):
                log(f"Starting live GUI monitor (showing last {args.gui_hours} hour(s))...")
                gui_process = subprocess.Popen([
                    sys.executable, 
                    gui_script,
                    '--hours', str(args.gui_hours),
                    '--file', DATA_FILE
                ])
                log(f"GUI monitor started with PID {gui_process.pid}")
            else:
                log(f"Warning: GUI script not found at {gui_script}", True)
        except Exception as e:
            log(f"Failed to start GUI monitor: {str(e)}", True)

signalHandler = SignalHandler()

translator = GXDLMSTranslator()
translator.blockCipherKey = GXByteBuffer(VNB_KEY)
translator.comments = True
#translator.completePdu = True
translator.hex = False  # Shows numeric values as int instead of hex -> <UInt16 Value="2319" /> instead of <UInt16 Value="090F" />

aesgcm = AESGCM(unhexlify(VNB_KEY))

ser = serial.Serial(
    port=COM_PORT,
    baudrate=BAUDRATE,
    parity=PARITY,
    stopbits=STOPBITS,
    bytesize=BYTESIZE,
    timeout=TIMEOUT
)

payload1StartPos = 27
payload2StartPos = 9

lastRealEnergyIn = 0
lastRealEnergyOut = 0
lastError = 0
errorCount = 0
measurementCounter = 0  # Counter for logging interval

while not signalHandler.shutdown_requested():
    try:
        data = ser.read(size=FRAME_LENGTH)

        if data == b"":
            continue

        if len(data) < FRAME_LENGTH and data[0:1] == FRAME1_START_BYTE and data[1:2] == data[2:3]:
            log("Incomplete message received. Try to get rest... Len: " + str(len(data)))
            rest = ser.read(size=FRAME_LENGTH - len(data))
            if len(data) + len(rest) == FRAME_LENGTH:
                data = data + rest
                log("Incomplete message completed. Len: " + str(len(data)))

        if len(data) < FRAME_LENGTH or data[0:1] != FRAME1_START_BYTE or data[-1:] != FRAME2_END_BYTE:
            log("Incomplete message received. Synchronize...")
            continue

        timestamp = int(time.time()) - 2

        # splitInfo = data[6]  # CI field - if this is x00, there's a second frame
        systemTitle = data[11:19]  # --- 8 bytes
        frameCounter = data[23:27]  # --- 4 bytes
        initVector = systemTitle + frameCounter  # --- 12 bytes

        frameLength1 = int(hex(data[1]), 16)  # FA --- 250 bytes
        frameLength2 = int(hex(data[frameLength1 + 7]), 16) # FA --- 38 Byte

        payload1 = data[payload1StartPos:(6 + frameLength1 - 2)]  # 6: Start bytes (M-Bus Data link layer) 2: end character + checksum
        payload2 = data[6 + frameLength1 + payload2StartPos:(frameLength1 + 5 + 5 + frameLength2)]

        cypherText = payload1 + payload2
        apdu = aesgcm.encrypt(initVector, cypherText, b"0").hex()

        xml = translator.pduToXml(apdu)
        soup = BeautifulSoup(xml, "lxml")

        # -> Do not use Smart Meter's time as it's about 20 seconds behind (in my case)
        # date = soup.find("datetime")
        # if not date:
        #     log("Could not retrieve datetime.", True)
        #     continue
        # date = date["value"]
        # year = int(date[0:4], 16)
        # month = int(date[4:6], 16)
        # day = int(date[6:8], 16)
        # hour = int(date[10:12], 16)
        # minute = int(date[12:14], 16)
        # second = int(date[14:16], 16)
        # #hundredthSecond = int(datetime[16:18], 16)
        # timestamp = int(datetime(year, month, day, hour, minute, second).timestamp())

        data = {}

        # Safer approach which analyzes the OBIS codes and does not depend on the order of the values
        structure_element = soup.find("structure")
        if not structure_element:
            log("Could not find structure element in XML. XML content: " + str(xml[:500]), True)
            continue
        
        elements = structure_element.find_all("structure", recursive=False)
        for el in elements:
            obisCode = el.find("octetstring")["value"]
            obisCode = ".".join("{!s}".format(int(obisCode[i:i+2], 16)) for (i) in range(0, 11, 2))
            if obisCode in OBIS:
                type = OBIS[obisCode]
                value = el.find("uint16") or el.find("uint32")
                if value and value["value"]:
                    data[type] = int(value["value"])
            elif obisCode != OBIS_DATE and obisCode not in OBIS_UNUSED:
                log("Message contains new and untracked OBIS code: " + obisCode)

        if len(data) == len(OBIS):
            realEnergyIn = data["RealEnergyIn"]
            realEnergyOut = data["RealEnergyOut"]
            realPowerIn = data["RealPowerIn"]
            realPowerOut = data["RealPowerOut"]
            realPowerNet = realPowerIn - realPowerOut
            
            # Increment measurement counter
            measurementCounter += 1
            
            # Log power data to CSV file (only every N-th measurement)
            if measurementCounter >= LOGGING_INTERVAL:
                log_power_data(timestamp, realPowerIn, realPowerOut, realPowerNet, realEnergyIn, realEnergyOut)
                measurementCounter = 0  # Reset counter
            
            print(os.linesep.join([
                "",
                "Timestamp:         " + datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                "VoltageL1:         " + str(data["VoltageL1"] / 10) + " V",
                "VoltageL2:         " + str(data["VoltageL2"] / 10) + " V",
                "VoltageL3:         " + str(data["VoltageL3"] / 10) + " V",
                "CurrentL1:         " + str(data["CurrentL1"] / 100) + " A",
                "CurrentL2:         " + str(data["CurrentL2"] / 100) + " A",
                "CurrentL3:         " + str(data["CurrentL3"] / 100) + " A",
                "RealPower:         " + str(realPowerNet) + " W",
                "RealPowerIn:       " + str(data["RealPowerIn"]) + " W",
                "RealPowerOut:      " + str(data["RealPowerOut"]) + " W",
                "RealEnergyIn:      " + str(data["RealEnergyIn"] / 1000) + " kWh",
                "RealEnergyInDiff:  " + str(realEnergyIn - lastRealEnergyIn) + " Wh",
                "RealEnergyOut:     " + str(data["RealEnergyOut"] / 1000) + " kWh",
                "RealEnergyOutDiff: " + str(realEnergyOut - lastRealEnergyOut) + " Wh",
                "ReactiveEnergyIn:  " + str(data["ReactiveEnergyIn"] / 1000) + " kvar",
                "ReactiveEnergyOut: " + str(data["ReactiveEnergyOut"] / 1000) + " kvar",
            ]))
            lastRealEnergyIn = realEnergyIn
            lastRealEnergyOut = realEnergyOut
        else:
            log("Only " + str(len(data)) + " values found in message" + (
                ": " + ",".join(data.keys()) if len(data) > 0 else ""), True)

        # Unsafer (and not really faster according to test) approach which depends on the order of the values sent
        # results_16 = soup.find_all("uint16")
        # results_32 = soup.find_all("uint32")
        #
        # if len(results_16) < 6 or len(results_32) < 6:
        #     log("Too little values found in message.", True)
        # else:
        #     print("Timestamp:", datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"))
        #     for key in data:
        #         print(key + ": ", data[key])

    except Exception as e:
        log(str(e), True)
        log(traceback.format_exc(), True)
        if lastError < time.time() - 300:
            errorCount = 1
        else:
            errorCount = errorCount + 1
        if errorCount > 5:
            log("Too many errors occurred. Shutdown...", True)
            break
        lastError = time.time()

ser.close()

# Cleanup GUI process if it was started
if gui_process is not None:
    try:
        log("Stopping GUI monitor...")
        gui_process.terminate()
        gui_process.wait(timeout=5)
        log("GUI monitor stopped")
    except Exception as e:
        log(f"Error stopping GUI monitor: {str(e)}", True)
        try:
            gui_process.kill()
        except:
            pass
