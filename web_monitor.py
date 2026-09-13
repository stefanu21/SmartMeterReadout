#!/usr/bin/env python3
"""
Web-based Live Monitor for Smart Meter Power Data.

Alternative to live_monitor.py (matplotlib GUI window): serves the same
power/energy data as an interactive web dashboard (Plotly.js), reachable
from any browser on the network. Useful for headless servers or remote
viewing without X11/VNC.
"""

import os
import sys
import json
import shutil
import argparse
from datetime import timedelta, datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

# Reuse the existing, well-tested data loading/parsing logic instead of
# duplicating it.
from plot_power_data import load_data, load_tasmota_data, TASMOTA_COLOR_PALETTE

# Configuration
DATA_FILE = "power_data.csv"
TASMOTA_DATA_FILE = "tasmota_power.csv"
DISPLAY_HOURS = 1        # Default initial view window
MAX_HISTORY_HOURS = 48   # Full history sent to the client (range-slider covers this)
REFRESH_MS = 5000        # Client polling interval

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Populated from CLI args in main()
app.config["DATA_FILE"] = os.path.join(BASE_DIR, DATA_FILE)
app.config["TASMOTA_FILE"] = os.path.join(BASE_DIR, TASMOTA_DATA_FILE)
app.config["DISPLAY_HOURS"] = DISPLAY_HOURS
app.config["REFRESH_MS"] = REFRESH_MS
# Optional second meter (shown alongside the first one)
app.config["DATA_FILE2"] = None
app.config["LABEL"] = "Zähler 1"
app.config["LABEL2"] = "Zähler 2"
# Optional device-name -> IP map for Tasmota plugs (shown as legend tooltips)
app.config["TASMOTA_IPS"] = {}


def _series(df, x_col, y_col):
    """Convert a DataFrame column pair into JSON-friendly lists."""
    x = df[x_col]
    if pd.api.types.is_datetime64_any_dtype(x):
        x = x.dt.strftime('%Y-%m-%dT%H:%M:%S')
    return {
        "x": x.tolist(),
        "y": df[y_col].astype(float).tolist(),
    }


def _pivot_series(pivot_df):
    """Convert a pivoted (datetime index, one column per device) DataFrame
    into a dict of device -> {x, y} series, skipping NaN gaps per-device."""
    result = {}
    for device in pivot_df.columns:
        col = pivot_df[device].dropna()
        result[str(device)] = {
            "x": col.index.strftime('%Y-%m-%dT%H:%M:%S').tolist(),
            "y": col.astype(float).tolist(),
        }
    return result


def _energy_15min(df):
    """Compute 15-minute-bucketed energy (kWh) in/out, same logic as
    live_monitor.py / plot_power_data.py."""
    df_sorted = df.sort_values('datetime').copy()
    df_sorted['energy_in_diff'] = df_sorted['real_energy_in'].diff()
    df_sorted['energy_out_diff'] = df_sorted['real_energy_out'].diff()
    df_sorted.loc[df_sorted['energy_in_diff'] < 0, 'energy_in_diff'] = 0
    df_sorted.loc[df_sorted['energy_out_diff'] < 0, 'energy_out_diff'] = 0

    df_sorted['time_15min'] = df_sorted['datetime'].dt.floor('15min')
    energy_15min = df_sorted.groupby('time_15min').agg({
        'energy_in_diff': 'sum',
        'energy_out_diff': 'sum'
    }).reset_index()

    energy_15min['energy_in_kwh'] = energy_15min['energy_in_diff'] / 1000
    energy_15min['energy_out_kwh'] = energy_15min['energy_out_diff'] / 1000

    return {
        "x": energy_15min['time_15min'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist(),
        "energy_in_kwh": energy_15min['energy_in_kwh'].tolist(),
        "energy_out_kwh": energy_15min['energy_out_kwh'].tolist(),
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        refresh_ms=app.config["REFRESH_MS"],
        display_hours=app.config["DISPLAY_HOURS"],
        label1=app.config["LABEL"],
        label2=app.config["LABEL2"],
    )


def _meter_block(df):
    """Build the {power, energy, stats} payload block for one meter's
    DataFrame (already loaded, non-empty)."""
    latest_time = df['datetime'].max()
    history_cutoff = latest_time - timedelta(hours=MAX_HISTORY_HOURS)
    dfh = df[df['datetime'] >= history_cutoff]
    return {
        "power": {
            "net": _series(dfh, 'datetime', 'real_power_net'),
            "in": _series(dfh, 'datetime', 'real_power_in'),
            "out": _series(dfh, 'datetime', 'real_power_out'),
        },
        "energy": _energy_15min(dfh),
        "stats": {
            "last_update": latest_time.strftime('%Y-%m-%d %H:%M:%S'),
            "current_power": float(dfh['real_power_net'].iloc[-1]),
            "avg_power": float(dfh['real_power_net'].mean()),
            "max_power": float(dfh['real_power_net'].max()),
            "min_power": float(dfh['real_power_net'].min()),
            "points": int(len(dfh)),
        },
    }


@app.route("/api/data")
def api_data():
    data_file = app.config["DATA_FILE"]
    tasmota_file = app.config["TASMOTA_FILE"]
    file2 = app.config.get("DATA_FILE2")

    # Optional: load a historical snapshot from archive/<stamp>/ instead of the
    # live files. Filenames inside an archive folder mirror the live ones.
    archive = request.args.get("archive")
    if archive:
        # Guard against path traversal: only a bare folder name is allowed.
        if "/" in archive or "\\" in archive or archive.startswith("."):
            return jsonify({"error": "Invalid archive name."}), 400
        adir = os.path.join(BASE_DIR, "archive", archive)
        if not os.path.isdir(adir):
            return jsonify({"error": "Archive not found."}), 404
        data_file = os.path.join(adir, os.path.basename(data_file))
        tasmota_file = os.path.join(adir, os.path.basename(tasmota_file))
        if file2:
            file2 = os.path.join(adir, os.path.basename(file2))

    try:
        df = load_data(data_file)
    except (FileNotFoundError, ValueError) as e:
        return jsonify({"error": str(e)}), 503

    if df.empty:
        return jsonify({"error": "No data available yet."}), 503

    latest_time = df['datetime'].max()
    history_cutoff = latest_time - timedelta(hours=MAX_HISTORY_HOURS)
    df_hist = df[df['datetime'] >= history_cutoff]

    payload = {
        "power": {
            "net": _series(df_hist, 'datetime', 'real_power_net'),
            "in": _series(df_hist, 'datetime', 'real_power_in'),
            "out": _series(df_hist, 'datetime', 'real_power_out'),
        },
        "energy": _energy_15min(df_hist),
        "tasmota": {},
        "tasmota_colors": {},
        "stats": {
            "last_update": latest_time.strftime('%Y-%m-%d %H:%M:%S'),
            "current_power": float(df_hist['real_power_net'].iloc[-1]),
            "avg_power": float(df_hist['real_power_net'].mean()),
            "max_power": float(df_hist['real_power_net'].max()),
            "min_power": float(df_hist['real_power_net'].min()),
            "points": int(len(df_hist)),
        },
        "display_hours": app.config["DISPLAY_HOURS"],
        "labels": {
            "meter1": app.config["LABEL"],
            "meter2": app.config["LABEL2"],
        },
    }

    # Optional second meter: shown alongside the first. If its file is not
    # there yet (reader just starting), simply omit it - no error.
    if file2:
        try:
            df2 = load_data(file2)
            if not df2.empty:
                block2 = _meter_block(df2)
                payload["power2"] = block2["power"]
                payload["energy2"] = block2["energy"]
                payload["stats2"] = block2["stats"]
        except (FileNotFoundError, ValueError):
            pass

    tasmota_pivot = load_tasmota_data(tasmota_file, hours=MAX_HISTORY_HOURS)
    if tasmota_pivot is not None:
        payload["tasmota"] = _pivot_series(tasmota_pivot)
        payload["tasmota_colors"] = {
            str(device): TASMOTA_COLOR_PALETTE[i % len(TASMOTA_COLOR_PALETTE)]
            for i, device in enumerate(tasmota_pivot.columns)
        }
        ip_map = app.config.get("TASMOTA_IPS") or {}
        payload["tasmota_ips"] = {
            str(device): ip_map.get(str(device), "")
            for device in tasmota_pivot.columns
        }

    return jsonify(payload)


@app.route("/api/archive", methods=["POST"])
def api_archive():
    """Archive the current measurement CSV files into a timestamped subfolder
    and start fresh. The reader processes open their CSV in append mode on every
    write and re-emit the header if the file is missing, so simply moving the
    files aside makes them recreate clean files automatically."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join(BASE_DIR, "archive", stamp)

    candidates = [
        app.config.get("DATA_FILE"),
        app.config.get("DATA_FILE2"),
        app.config.get("TASMOTA_FILE"),
    ]

    moved = []
    try:
        os.makedirs(archive_dir, exist_ok=True)
        for path in candidates:
            if path and os.path.isfile(path):
                dest = os.path.join(archive_dir, os.path.basename(path))
                shutil.move(path, dest)
                moved.append(os.path.basename(path))
    except OSError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({
        "status": "ok",
        "archive": os.path.join("archive", stamp),
        "moved": moved,
    })


@app.route("/api/archives")
def api_archives():
    """List available archive snapshots (newest first)."""
    root = os.path.join(BASE_DIR, "archive")
    entries = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                entries.append(name)
    entries.sort(reverse=True)
    return jsonify({"archives": entries})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def main():
    parser = argparse.ArgumentParser(description='Web-based Live Monitor for Smart Meter Data')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host/IP to bind the web server to (default: 0.0.0.0 - reachable from the LAN)')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port to bind the web server to (default: 8080)')
    parser.add_argument('--hours', type=float, default=DISPLAY_HOURS,
                       help=f'Initial display window in hours (default: {DISPLAY_HOURS}). '
                            f'Full {MAX_HISTORY_HOURS}h history is still available via the range slider.')
    parser.add_argument('--refresh', type=int, default=REFRESH_MS,
                       help=f'Client polling interval in milliseconds (default: {REFRESH_MS})')
    parser.add_argument('--file', type=str, default=DATA_FILE,
                       help=f'Path to CSV data file (default: {DATA_FILE})')
    parser.add_argument('--tasmota-file', type=str, default=TASMOTA_DATA_FILE,
                       help=f'Path to Tasmota smart-plug CSV file (default: {TASMOTA_DATA_FILE}). '
                            f'Ignored if the file does not exist.')
    parser.add_argument('--file2', type=str, default=None,
                       help='Optional path to a second meter CSV file, shown alongside the first.')
    parser.add_argument('--label', type=str, default='Zähler 1',
                       help='Display label for the first meter (default: "Zähler 1")')
    parser.add_argument('--label2', type=str, default='Zähler 2',
                       help='Display label for the second meter (default: "Zähler 2")')
    parser.add_argument('--tasmota-devices', type=str, default=None,
                       help='Comma-separated Name=IP list of Tasmota devices, used to '
                            'show the IP as a legend tooltip (e.g. "Boiler=192.168.100.3").')
    args = parser.parse_args()

    app.config["DATA_FILE"] = os.path.join(BASE_DIR, args.file) if not os.path.isabs(args.file) else args.file
    app.config["TASMOTA_FILE"] = os.path.join(BASE_DIR, args.tasmota_file) if not os.path.isabs(args.tasmota_file) else args.tasmota_file
    app.config["DISPLAY_HOURS"] = args.hours
    app.config["REFRESH_MS"] = args.refresh
    app.config["LABEL"] = args.label
    app.config["LABEL2"] = args.label2
    if args.tasmota_devices:
        ip_map = {}
        for entry in args.tasmota_devices.split(","):
            entry = entry.strip()
            if "=" in entry:
                name, ip = entry.split("=", 1)
                ip_map[name.strip()] = ip.strip()
        app.config["TASMOTA_IPS"] = ip_map
    if args.file2:
        app.config["DATA_FILE2"] = os.path.join(BASE_DIR, args.file2) if not os.path.isabs(args.file2) else args.file2

    print("=" * 70)
    print("Smart Meter Web Monitor")
    print("=" * 70)
    print(f"Data file: {app.config['DATA_FILE']}")
    print(f"Tasmota file: {app.config['TASMOTA_FILE']}")
    if app.config.get("DATA_FILE2"):
        print(f"Second meter file: {app.config['DATA_FILE2']}")
        print(f"Labels: '{app.config['LABEL']}' / '{app.config['LABEL2']}'")
    print(f"Display window: last {args.hours} hour(s) (up to {MAX_HISTORY_HOURS}h via range slider)")
    print(f"Refresh interval: {args.refresh / 1000} seconds")
    print("-" * 70)
    print(f"Starting web server on http://{args.host}:{args.port}/")
    if args.host == '0.0.0.0':
        print("NOTE: Server is reachable from any device on your local network.")
        print("      This is Flask's built-in dev server - no authentication, not")
        print("      hardened for production use. Only use on trusted networks.")
    print("Press Ctrl+C to stop.")
    print("=" * 70)

    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
