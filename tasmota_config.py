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
Shared Tasmota device configuration.

The list of Tasmota smart plugs to poll lives in a small JSON config file so it
can be managed from the web UI at runtime (add/remove) and picked up by the
background poller without a restart. Both tasmota_monitor.py (reader) and
web_monitor.py (web UI / REST API) use this module as the single source of
truth.

File format::

    { "devices": [ { "name": "Boiler", "ip": "192.168.100.3" }, ... ] }

All writes are atomic (temp file + os.replace) so a concurrent reader never
sees a half-written file.
"""

import os
import re
import json
import tempfile

DEFAULT_CONFIG_FILENAME = "tasmota_devices.json"

# A device name is used as a CSV column / legend label and as a URL path
# segment in the REST API, so keep it to a sane, safe character set.
_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,64}$")
# Accept IPv4 addresses or simple hostnames (no scheme, no path).
_IP_RE = re.compile(r"^[A-Za-z0-9.\-]{1,255}$")


class DeviceConfigError(ValueError):
    """Raised for invalid device input or duplicate/unknown device names."""


def default_config_path(base_dir):
    """Return the default config path located next to the scripts."""
    return os.path.join(base_dir, DEFAULT_CONFIG_FILENAME)


def validate_name(name):
    name = (name or "").strip()
    if not _NAME_RE.match(name):
        raise DeviceConfigError(
            "Invalid device name (allowed: letters, digits, space, _.- ; 1-64 chars)."
        )
    return name


def validate_ip(ip):
    ip = (ip or "").strip()
    if not _IP_RE.match(ip):
        raise DeviceConfigError("Invalid IP address or hostname.")
    return ip


def load_devices(path):
    """Load the device list from the JSON config. Returns a list of
    {"name": str, "ip": str} dicts. Missing or malformed files yield an empty
    list (the poller then simply idles until devices are added)."""
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []

    devices = []
    for entry in (data or {}).get("devices", []):
        try:
            name = validate_name(entry.get("name"))
            ip = validate_ip(entry.get("ip"))
        except (DeviceConfigError, AttributeError):
            continue
        devices.append({"name": name, "ip": ip})
    return devices


def save_devices(path, devices):
    """Atomically write the device list to the JSON config."""
    payload = {"devices": [{"name": d["name"], "ip": d["ip"]} for d in devices]}
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tasmota_devices_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def add_device(path, name, ip):
    """Add a device (validated) to the config. Raises DeviceConfigError on
    invalid input or a duplicate name. Returns the updated device list."""
    name = validate_name(name)
    ip = validate_ip(ip)
    devices = load_devices(path)
    if any(d["name"].lower() == name.lower() for d in devices):
        raise DeviceConfigError(f"A device named '{name}' already exists.")
    devices.append({"name": name, "ip": ip})
    save_devices(path, devices)
    return devices


def remove_device(path, name):
    """Remove the device with the given name. Raises DeviceConfigError if it is
    not present. Returns the updated device list."""
    name = (name or "").strip()
    devices = load_devices(path)
    remaining = [d for d in devices if d["name"].lower() != name.lower()]
    if len(remaining) == len(devices):
        raise DeviceConfigError(f"No device named '{name}'.")
    save_devices(path, remaining)
    return remaining


def rename_device(path, old_name, new_name):
    """Rename the device ``old_name`` to ``new_name`` (validated). Raises
    DeviceConfigError if the old device is missing or the new name collides with
    a different existing device. A pure case change of the same device is
    allowed. Returns the updated device list.

    Note: only affects live polling/legend going forward. Rows already written
    to the CSV keep the old column name until the next archive.
    """
    old_name = (old_name or "").strip()
    new_name = validate_name(new_name)
    devices = load_devices(path)

    target = next((d for d in devices if d["name"].lower() == old_name.lower()), None)
    if target is None:
        raise DeviceConfigError(f"No device named '{old_name}'.")

    if any(
        d is not target and d["name"].lower() == new_name.lower()
        for d in devices
    ):
        raise DeviceConfigError(f"A device named '{new_name}' already exists.")

    target["name"] = new_name
    save_devices(path, devices)
    return devices


def devices_as_ip_map(devices):
    """Return a {name: ip} dict for the given device list."""
    return {d["name"]: d["ip"] for d in devices}
