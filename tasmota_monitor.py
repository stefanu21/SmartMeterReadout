#!/usr/bin/env python3
#
# Copyright (C) 2023-2026 the SmartMeterReadout authors and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Tasmota Smart Plug Power Monitor.

Polls one or more Tasmota smart plugs over HTTP (Status 10 command) and logs
their power/energy readings to a CSV file, in the same style as
readout-smart-meter.py, so the data can be displayed alongside the smart
meter power curves in live_monitor.py / plot_power_data.py.
"""

import os
import sys
import json
import time
import signal
import argparse
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# -- CONFIGURATION BEGIN -- #

# Tasmota devices to poll: friendly name -> IP address (or hostname).
# Can be overridden/extended via --devices "Name1=IP1,Name2=IP2"
TASMOTA_DEVICES = {
    "Geraet1": "192.168.100.3",
}

POLL_INTERVAL = 5       # Seconds between poll cycles (matches smart meter cadence)
REQUEST_TIMEOUT = 3     # Seconds per HTTP request, per device

LOG_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), os.path.basename(__file__)[:-2] + "log"))
# LOG_FILE = ""  # if you don't want to log
PRINT_LOGS = True

DATA_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), "tasmota_power.csv"))
ENABLE_DATA_LOGGING = True

CSV_HEADER = "timestamp,datetime,device,power,voltage,current,energy_today,energy_yesterday,energy_total\n"

# -- CONFIGURATION END -- #


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


def log_tasmota_data(timestamp, device, power, voltage, current, energy_today, energy_yesterday, energy_total):
    """Log a single device's reading to CSV file for later graphing. Appends to existing file."""
    global DATA_FILE, ENABLE_DATA_LOGGING
    if not ENABLE_DATA_LOGGING:
        return

    try:
        file_exists = os.path.isfile(DATA_FILE)
        write_header = False

        if not file_exists:
            write_header = True
        elif os.path.getsize(DATA_FILE) == 0:
            write_header = True

        with open(DATA_FILE, "a") as data_file:
            if write_header:
                data_file.write(CSV_HEADER)

            dt_string = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            data_file.write(
                f"{timestamp},{dt_string},{device},{power},{voltage},{current},"
                f"{energy_today},{energy_yesterday},{energy_total}\n"
            )
    except Exception as e:
        log(f"Error writing Tasmota data: {str(e)}", True)


class SignalHandler:
    _shutdown = False

    def __init__(self):
        signal.signal(signal.SIGINT, self._request_shutdown)
        signal.signal(signal.SIGTERM, self._request_shutdown)

    def _request_shutdown(self, *args):
        log('Request to shutdown received. Stopping...')
        self._shutdown = True

    def shutdown_requested(self):
        return self._shutdown


def parse_devices(devices_arg):
    """Parse a 'Name1=IP1,Name2=IP2' string into a dict. Returns the default
    TASMOTA_DEVICES dict if devices_arg is None/empty."""
    if not devices_arg:
        return dict(TASMOTA_DEVICES)

    devices = {}
    for entry in devices_arg.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            log(f"Ignoring invalid device entry (expected Name=IP): '{entry}'", True)
            continue
        name, ip = entry.split("=", 1)
        devices[name.strip()] = ip.strip()
    return devices


def _as_scalar(value):
    """Tasmota can report Power/Voltage/Current as a single number or, for
    multi-channel devices, as a list of numbers (one per channel). Sum lists
    to get a single total value for the device."""
    if isinstance(value, (list, tuple)):
        try:
            return sum(float(v) for v in value)
        except (TypeError, ValueError):
            return 0.0
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def poll_device(name, ip):
    """Query a single Tasmota device's Status 10 endpoint and return a dict
    with the parsed ENERGY values, or None on failure."""
    url = f"http://{ip}/cm?cmnd=Status%2010"
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log(f"[{name}] Request failed: {str(e)}", True)
        return None
    except json.JSONDecodeError as e:
        log(f"[{name}] Invalid JSON response: {str(e)}", True)
        return None

    sns = payload.get("StatusSNS", payload)
    energy = sns.get("ENERGY")
    if not energy:
        log(f"[{name}] No ENERGY data in response (device may not support power monitoring).", True)
        return None

    return {
        "name": name,
        "power": _as_scalar(energy.get("Power")),
        "voltage": _as_scalar(energy.get("Voltage")),
        "current": _as_scalar(energy.get("Current")),
        "energy_today": _as_scalar(energy.get("Today")),
        "energy_yesterday": _as_scalar(energy.get("Yesterday")),
        "energy_total": _as_scalar(energy.get("Total")),
    }


def main():
    global DATA_FILE, POLL_INTERVAL

    parser = argparse.ArgumentParser(description='Tasmota Smart Plug Power Monitor')
    parser.add_argument('--devices', type=str,
                         help='Comma-separated list of Name=IP devices to poll, '
                              'e.g. "Kueche=192.168.100.3,Keller=192.168.100.4" '
                              '(default: built-in TASMOTA_DEVICES config)')
    parser.add_argument('--interval', type=float, default=POLL_INTERVAL,
                         help=f'Seconds between poll cycles (default: {POLL_INTERVAL})')
    parser.add_argument('--file', type=str, default=DATA_FILE,
                         help=f'Path to CSV output file (default: {DATA_FILE})')
    parser.add_argument('--clear-data', action='store_true',
                         help='Delete old data and start fresh (creates backup as tasmota_power.csv.backup)')
    args = parser.parse_args()

    DATA_FILE = os.path.realpath(args.file)
    POLL_INTERVAL = args.interval
    devices = parse_devices(args.devices)

    if not devices:
        log("No Tasmota devices configured. Use --devices or edit TASMOTA_DEVICES.", True)
        sys.exit(1)

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
        try:
            with open(DATA_FILE, 'w') as f:
                f.write(CSV_HEADER)
            log("Old data cleared. Starting fresh with new file.")
        except Exception as e:
            log(f"Error creating new data file: {str(e)}", True)
            sys.exit(1)

    log("Start " + os.path.basename(__file__))
    log(f"Polling {len(devices)} Tasmota device(s) every {POLL_INTERVAL}s: "
        + ", ".join(f"{n} ({ip})" for n, ip in devices.items()))
    log(f"Logging to: {DATA_FILE}")

    signalHandler = SignalHandler()

    with ThreadPoolExecutor(max_workers=max(1, len(devices))) as executor:
        while not signalHandler.shutdown_requested():
            cycle_start = time.time()
            timestamp = int(cycle_start)

            try:
                results = executor.map(lambda item: poll_device(*item), devices.items())
                for result in results:
                    if result is None:
                        continue
                    log_tasmota_data(
                        timestamp,
                        result["name"],
                        result["power"],
                        result["voltage"],
                        result["current"],
                        result["energy_today"],
                        result["energy_yesterday"],
                        result["energy_total"],
                    )
            except Exception as e:
                log(str(e), True)
                log(traceback.format_exc(), True)

            elapsed = time.time() - cycle_start
            remaining = POLL_INTERVAL - elapsed
            if remaining > 0:
                # Sleep in small increments so shutdown is responsive
                sleep_until = time.time() + remaining
                while time.time() < sleep_until and not signalHandler.shutdown_requested():
                    time.sleep(min(0.2, sleep_until - time.time()))

    log("Tasmota monitor stopped.")


if __name__ == "__main__":
    main()
