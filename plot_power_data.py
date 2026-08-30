#!/usr/bin/env python3
"""
Script to visualize power consumption data from smart meter.
Reads power_data.csv and creates various plots.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import sys
import os
import time

# Try to import mplcursors for interactive cursor
try:
    import mplcursors
    HAS_MPLCURSORS = True
except ImportError:
    HAS_MPLCURSORS = False

# Configuration
DATA_FILE = "power_data.csv"
TASMOTA_DATA_FILE = "tasmota_power.csv"
OUTPUT_DIR = "plots"

# Colors used for Tasmota smart-plug lines, distinct from the smart meter's
# blue (net) / red (in) / green (out).
TASMOTA_COLOR_PALETTE = [
    'purple', 'orange', 'brown', 'magenta', 'cyan', 'olive', 'darkgoldenrod', 'teal',
]

def load_tasmota_data(filepath, hours=24):
    """Load Tasmota smart-plug data (long format CSV: one row per device per
    poll cycle) and pivot it into a wide DataFrame (datetime index, one
    column per device holding its power in Watts). Returns None if the file
    doesn't exist or has no usable data."""
    if not filepath or not os.path.exists(filepath):
        return None

    try:
        df = pd.read_csv(filepath, on_bad_lines='skip')
        if df.empty or 'device' not in df.columns or 'power' not in df.columns:
            return None

        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        df['power'] = pd.to_numeric(df['power'], errors='coerce')
        df = df.dropna(subset=['datetime', 'power'])
        if df.empty:
            return None

        latest_time = df['datetime'].max()
        cutoff_time = latest_time - timedelta(hours=hours)
        df = df[df['datetime'] >= cutoff_time]
        if df.empty:
            return None

        return df.pivot_table(index='datetime', columns='device', values='power', aggfunc='last')
    except Exception as e:
        print(f"Warning: Could not load Tasmota data: {e}")
        return None

def _tasmota_color_map(devices):
    """Assign a stable color to each device name from the palette."""
    return {device: TASMOTA_COLOR_PALETTE[i % len(TASMOTA_COLOR_PALETTE)]
            for i, device in enumerate(devices)}

def clamp_ylim_nonnegative(ax, values):
    """After autoscale, raise the y-axis lower limit to 0 if none of the
    plotted power values are actually negative (avoids a misleading
    negative-looking axis when the meter never feeds power back in)."""
    try:
        data_min = float(min(v.min() for v in values if len(v) > 0))
    except ValueError:
        return
    if data_min >= 0:
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(max(0, ymin), ymax)

def load_data(filepath):
    """Load power data from CSV file."""
    if not os.path.exists(filepath):
        print(f"Error: Data file '{filepath}' not found.")
        print(f"Make sure the smart meter readout script is running and collecting data.")
        sys.exit(1)
    
    try:
        # First, check the header to determine format
        with open(filepath, 'r') as f:
            header = f.readline().strip()
        
        # Determine if we have energy columns
        has_energy = 'real_energy_in' in header
        
        if has_energy:
            # New format with energy columns
            df = pd.read_csv(filepath)
        else:
            # Old format without energy columns - add them as zeros
            df = pd.read_csv(filepath)
            df['real_energy_in'] = 0
            df['real_energy_out'] = 0
        
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Handle mixed format files (old rows might not have all columns)
        # Fill NaN values with 0 for energy columns
        if 'real_energy_in' in df.columns:
            df['real_energy_in'] = df['real_energy_in'].fillna(0)
        if 'real_energy_out' in df.columns:
            df['real_energy_out'] = df['real_energy_out'].fillna(0)
        
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        print("\nTrying to fix mixed format CSV...")
        
        # Try to handle mixed format by reading line by line
        try:
            data_rows = []
            with open(filepath, 'r') as f:
                header_line = f.readline().strip()
                headers = header_line.split(',')
                
                # Determine column count
                expected_cols = len(headers)
                has_energy = 'real_energy_in' in headers
                
                for line_num, line in enumerate(f, start=2):
                    parts = line.strip().split(',')
                    
                    # Handle rows with fewer columns (old format)
                    if len(parts) < expected_cols:
                        # Add missing energy columns as 0
                        while len(parts) < expected_cols:
                            parts.append('0')
                    
                    # Handle rows with too many columns (shouldn't happen but just in case)
                    elif len(parts) > expected_cols:
                        parts = parts[:expected_cols]
                    
                    data_rows.append(parts)
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Convert to proper types
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df['real_power_in'] = pd.to_numeric(df['real_power_in'], errors='coerce').fillna(0)
            df['real_power_out'] = pd.to_numeric(df['real_power_out'], errors='coerce').fillna(0)
            df['real_power_net'] = pd.to_numeric(df['real_power_net'], errors='coerce').fillna(0)
            
            if has_energy:
                df['real_energy_in'] = pd.to_numeric(df['real_energy_in'], errors='coerce').fillna(0)
                df['real_energy_out'] = pd.to_numeric(df['real_energy_out'], errors='coerce').fillna(0)
            else:
                df['real_energy_in'] = 0
                df['real_energy_out'] = 0
            
            # Remove rows with invalid datetime
            df = df.dropna(subset=['datetime'])
            
            print(f"✓ Successfully loaded {len(df)} data points")
            return df
            
        except Exception as e2:
            print(f"Error: Could not load data: {e2}")
            print("\nThe CSV file may be corrupted or in an incompatible format.")
            print("You may need to regenerate the data file.")
            sys.exit(1)

def plot_power_overview(df, hours=24, tasmota_file=None):
    """Plot RealPower (net), RealPowerIn and RealPowerOut in one graph."""
    if df.empty:
        print(f"No data available.")
        return
    
    # Use latest timestamp in data as reference (not current time)
    latest_time = df['datetime'].max()
    cutoff_time = latest_time - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        print(f"Data range: {df['datetime'].min()} to {df['datetime'].max()}")
        return
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Plot all three power values
    ax.plot(df_filtered['datetime'], df_filtered['real_power_net'], 
            label='RealPower (Net)', linewidth=2, color='blue')
    ax.plot(df_filtered['datetime'], df_filtered['real_power_in'], 
            label='RealPowerIn (Consumption)', linewidth=1.5, color='red', alpha=0.7)
    ax.plot(df_filtered['datetime'], df_filtered['real_power_out'], 
            label='RealPowerOut (Feed-in)', linewidth=1.5, color='green', alpha=0.7)
    
    # Plot Tasmota smart-plug devices, if available
    tasmota_df = load_tasmota_data(tasmota_file, hours=hours)
    clamp_values = [df_filtered['real_power_net'], df_filtered['real_power_in'], df_filtered['real_power_out']]
    if tasmota_df is not None:
        colors = _tasmota_color_map(tasmota_df.columns)
        for device in tasmota_df.columns:
            ax.plot(tasmota_df.index, tasmota_df[device],
                    label=str(device), linewidth=1.5, color=colors[device])
            clamp_values.append(tasmota_df[device].dropna())
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Power (W)', fontsize=12)
    ax.set_title(f'Power Overview - Last {hours} Hours', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    clamp_ylim_nonnegative(ax, clamp_values)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    if hours <= 2:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
    elif hours <= 12:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    else:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'power_overview_{hours}h.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    
    plt.close()

def plot_energy_overview(df, hours=24):
    """Plot RealEnergyIn and RealEnergyOut as bar chart with 15-minute intervals."""
    if df.empty:
        print(f"No data available.")
        return
    
    # Use latest timestamp in data as reference (not current time)
    latest_time = df['datetime'].max()
    cutoff_time = latest_time - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time].copy()
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        print(f"Data range: {df['datetime'].min()} to {df['datetime'].max()}")
        return
    
    # Check if energy data exists
    if df_filtered['real_energy_in'].sum() == 0 and df_filtered['real_energy_out'].sum() == 0:
        print("Warning: No energy data available. Skipping energy plot.")
        return
    
    # Calculate energy consumption per 15-minute interval
    # Energy counters are cumulative, so we need the difference
    df_filtered = df_filtered.sort_values('datetime')
    df_filtered['energy_in_diff'] = df_filtered['real_energy_in'].diff()
    df_filtered['energy_out_diff'] = df_filtered['real_energy_out'].diff()
    
    # Remove negative differences (can happen on counter resets)
    df_filtered.loc[df_filtered['energy_in_diff'] < 0, 'energy_in_diff'] = 0
    df_filtered.loc[df_filtered['energy_out_diff'] < 0, 'energy_out_diff'] = 0
    
    # Group by 15-minute intervals
    df_filtered['time_15min'] = df_filtered['datetime'].dt.floor('15min')
    energy_15min = df_filtered.groupby('time_15min').agg({
        'energy_in_diff': 'sum',
        'energy_out_diff': 'sum'
    }).reset_index()
    
    # Convert Wh to kWh
    energy_15min['energy_in_kwh'] = energy_15min['energy_in_diff'] / 1000
    energy_15min['energy_out_kwh'] = energy_15min['energy_out_diff'] / 1000
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Create bar chart
    bar_width = 0.35
    x = range(len(energy_15min))
    
    # Bars for energy in (consumption)
    bars_in = ax.bar([i - bar_width/2 for i in x], energy_15min['energy_in_kwh'], 
                     bar_width, label='Energy In (Consumption)', color='red', alpha=0.7)
    
    # Bars for energy out (feed-in)
    bars_out = ax.bar([i + bar_width/2 for i in x], energy_15min['energy_out_kwh'], 
                      bar_width, label='Energy Out (Feed-in)', color='green', alpha=0.7)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Energy per 15 min (kWh)', fontsize=12)
    ax.set_title(f'Energy Consumption - 15 Minute Intervals (Last {hours} Hours)', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Format x-axis
    ax.set_xticks(x)
    labels = [t.strftime('%H:%M') for t in energy_15min['time_15min']]
    ax.set_xticklabels(labels, rotation=45, ha='right')
    
    # Only show every nth label if too many
    if len(labels) > 20:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0:
                label.set_visible(False)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'energy_overview_{hours}h.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    
    plt.close()

def plot_daily_summary(df):
    """Plot daily summary statistics."""
    df['date'] = df['datetime'].dt.date
    
    daily_stats = df.groupby('date').agg({
        'real_power_in': ['mean', 'max'],
        'real_power_out': ['mean', 'max'],
        'real_power_net': ['mean', 'min', 'max']
    }).reset_index()
    
    if daily_stats.empty:
        print("No data available for daily summary.")
        return
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    x = range(len(daily_stats))
    dates = [str(d) for d in daily_stats['date']]
    
    ax.bar(x, daily_stats[('real_power_net', 'mean')], 
           label='Average Net Power', alpha=0.7, color='blue')
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Power (W)', fontsize=12)
    ax.set_title('Daily Average Power Consumption', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, 'daily_summary.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    
    plt.close()

def print_statistics(df, hours=24):
    """Print basic statistics about the power data."""
    if df.empty:
        print(f"No data available.")
        return
    
    # Use latest timestamp in data as reference (not current time)
    latest_time = df['datetime'].max()
    cutoff_time = latest_time - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    print(f"\n{'='*60}")
    print(f"Power Statistics - Last {hours} Hours")
    print(f"{'='*60}")
    print(f"Time range: {df_filtered['datetime'].min()} to {df_filtered['datetime'].max()}")
    print(f"Number of measurements: {len(df_filtered)}")
    print(f"\nNet Power (real_power_net):")
    print(f"  Average: {df_filtered['real_power_net'].mean():.1f} W")
    print(f"  Maximum: {df_filtered['real_power_net'].max():.1f} W")
    print(f"  Minimum: {df_filtered['real_power_net'].min():.1f} W")
    print(f"\nPower Consumption (real_power_in):")
    print(f"  Average: {df_filtered['real_power_in'].mean():.1f} W")
    print(f"  Maximum: {df_filtered['real_power_in'].max():.1f} W")
    print(f"\nPower Feed-in (real_power_out):")
    print(f"  Average: {df_filtered['real_power_out'].mean():.1f} W")
    print(f"  Maximum: {df_filtered['real_power_out'].max():.1f} W")
    
    # Energy statistics if available
    if df_filtered['real_energy_in'].sum() > 0 or df_filtered['real_energy_out'].sum() > 0:
        energy_in_start = df_filtered['real_energy_in'].iloc[0] / 1000
        energy_in_end = df_filtered['real_energy_in'].iloc[-1] / 1000
        energy_out_start = df_filtered['real_energy_out'].iloc[0] / 1000
        energy_out_end = df_filtered['real_energy_out'].iloc[-1] / 1000
        
        print(f"\nEnergy Counters:")
        print(f"  RealEnergyIn:  {energy_in_start:.2f} kWh → {energy_in_end:.2f} kWh (Δ {energy_in_end - energy_in_start:.3f} kWh)")
        print(f"  RealEnergyOut: {energy_out_start:.2f} kWh → {energy_out_end:.2f} kWh (Δ {energy_out_end - energy_out_start:.3f} kWh)")
    
    print(f"{'='*60}\n")

class PlotNavigator:
    """Adds mouse-wheel and keyboard navigation to a static (non-live) plot.

    Controls (mirrors live_monitor.py):
      - Mouse wheel:          Scroll Y-axis up/down (pan)
      - Shift + mouse wheel:   Zoom Y-axis in/out
      - Ctrl + mouse wheel:    Zoom X-axis in/out
      - Up / Down arrows:      Scroll Y-axis up/down
      - Left / Right arrows:   Scroll X-axis (time) left/right
      - '+' / '-':             Zoom Y-axis in/out
      - 'r':                   Reset to the original view
    """

    def __init__(self, fig, ax):
        self.fig = fig
        self.ax = ax
        # Remember the initial view so 'r' can restore it
        self._home_xlim = ax.get_xlim()
        self._home_ylim = ax.get_ylim()
        # Throttle keyboard events to avoid backlog / "running on" after release
        self._last_key_time = 0.0
        self._key_min_interval = 0.05
        fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        fig.canvas.mpl_connect('key_press_event', self.on_key)

    def _get_data_yrange(self):
        """Return (data_min, data_max) of all line data in the axes."""
        data_min = None
        data_max = None
        for line in self.ax.get_lines():
            ydata = line.get_ydata()
            if ydata is None or len(ydata) == 0:
                continue
            try:
                ymin = float(np.nanmin(ydata))
                ymax = float(np.nanmax(ydata))
            except (ValueError, TypeError):
                continue
            data_min = ymin if data_min is None else min(data_min, ymin)
            data_max = ymax if data_max is None else max(data_max, ymax)
        return data_min, data_max

    def _clamp_ypan(self, new_ymin, new_ymax):
        """Clamp a proposed Y-view so the measurement data stays visible."""
        data_min, data_max = self._get_data_yrange()
        if data_min is None:
            return new_ymin, new_ymax
        view_height = new_ymax - new_ymin
        max_ymin = data_max - view_height * 0.1
        min_ymin = data_min - view_height * 0.9
        clamped_ymin = max(min_ymin, min(new_ymin, max_ymin))
        if data_min >= 0:
            clamped_ymin = max(0, clamped_ymin)
        clamped_ymax = clamped_ymin + view_height
        return clamped_ymin, clamped_ymax

    def on_scroll(self, event):
        if event.inaxes is not self.ax:
            return
        ax = self.ax
        step = event.step
        key = event.key

        if key == 'control':
            xmin, xmax = ax.get_xlim()
            xrange = xmax - xmin
            scale = 0.9 if step > 0 else 1.1
            xdata = event.xdata if event.xdata is not None else (xmin + xmax) / 2
            new_range = xrange * scale
            left_frac = (xdata - xmin) / xrange
            ax.set_xlim(xdata - new_range * left_frac,
                        xdata + new_range * (1 - left_frac))
        elif key == 'shift':
            ymin, ymax = ax.get_ylim()
            yrange = ymax - ymin
            scale = 0.9 if step > 0 else 1.1
            ydata = event.ydata if event.ydata is not None else (ymin + ymax) / 2
            new_range = yrange * scale
            bottom_frac = (ydata - ymin) / yrange
            ax.set_ylim(ydata - new_range * bottom_frac,
                        ydata + new_range * (1 - bottom_frac))
        else:
            ymin, ymax = ax.get_ylim()
            shift = (ymax - ymin) * 0.1 * step
            new_ymin, new_ymax = self._clamp_ypan(ymin + shift, ymax + shift)
            ax.set_ylim(new_ymin, new_ymax)

        self.fig.canvas.draw_idle()

    def on_key(self, event):
        if event.key == 'r':
            self.ax.set_xlim(self._home_xlim)
            self.ax.set_ylim(self._home_ylim)
            self.fig.canvas.draw_idle()
            return

        if event.key not in ('up', 'down', 'left', 'right', '+', '=', '-'):
            return

        # Throttle to avoid an event backlog that keeps the plot moving
        now = time.monotonic()
        if now - self._last_key_time < self._key_min_interval:
            return
        self._last_key_time = now

        ax = self.ax
        if event.key == 'up':
            ymin, ymax = ax.get_ylim()
            shift = (ymax - ymin) * 0.1
            ax.set_ylim(*self._clamp_ypan(ymin + shift, ymax + shift))
        elif event.key == 'down':
            ymin, ymax = ax.get_ylim()
            shift = (ymax - ymin) * 0.1
            ax.set_ylim(*self._clamp_ypan(ymin - shift, ymax - shift))
        elif event.key == 'right':
            xmin, xmax = ax.get_xlim()
            shift = (xmax - xmin) * 0.1
            ax.set_xlim(xmin + shift, xmax + shift)
        elif event.key == 'left':
            xmin, xmax = ax.get_xlim()
            shift = (xmax - xmin) * 0.1
            ax.set_xlim(xmin - shift, xmax - shift)
        elif event.key in ('+', '='):
            ymin, ymax = ax.get_ylim()
            center = (ymin + ymax) / 2
            half = (ymax - ymin) / 2 * 0.9
            ax.set_ylim(center - half, center + half)
        elif event.key == '-':
            ymin, ymax = ax.get_ylim()
            center = (ymin + ymax) / 2
            half = (ymax - ymin) / 2 * 1.1
            ax.set_ylim(center - half, center + half)

        self.fig.canvas.draw_idle()


def plot_power_overview_interactive(df, hours=24, tasmota_file=None):
    """Interactive version of power overview plot."""
    if df.empty:
        print(f"No data available.")
        return
    
    latest_time = df['datetime'].max()
    cutoff_time = latest_time - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    line_net = ax.plot(df_filtered['datetime'], df_filtered['real_power_net'], 
                       label='RealPower (Net)', linewidth=2, color='blue')
    line_in = ax.plot(df_filtered['datetime'], df_filtered['real_power_in'], 
                      label='RealPowerIn (Consumption)', linewidth=1.5, color='red', alpha=0.7)
    line_out = ax.plot(df_filtered['datetime'], df_filtered['real_power_out'], 
                       label='RealPowerOut (Feed-in)', linewidth=1.5, color='green', alpha=0.7)
    
    # Plot Tasmota smart-plug devices, if available
    tasmota_df = load_tasmota_data(tasmota_file, hours=hours)
    tasmota_lines = []
    clamp_values = [df_filtered['real_power_net'], df_filtered['real_power_in'], df_filtered['real_power_out']]
    if tasmota_df is not None:
        colors = _tasmota_color_map(tasmota_df.columns)
        for device in tasmota_df.columns:
            tasmota_lines += ax.plot(tasmota_df.index, tasmota_df[device],
                                      label=str(device), linewidth=1.5, color=colors[device])
            clamp_values.append(tasmota_df[device].dropna())
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Power (W)', fontsize=12)
    ax.set_title(f'Power Overview - Last {hours} Hours (INTERACTIVE)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    clamp_ylim_nonnegative(ax, clamp_values)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Enable mouse-wheel / keyboard navigation (scroll, zoom, pan, reset)
    ax._navigator = PlotNavigator(fig, ax)
    
    # Add interactive cursor if mplcursors is available
    if HAS_MPLCURSORS:
        # Use hover=2 (Transient) to snap to nearest data point
        # This shows tooltips when hovering near the line and snaps to actual measurements
        cursor = mplcursors.cursor(line_net + line_in + line_out + tasmota_lines, hover=2)
        
        @cursor.connect("add")
        def on_add(sel):
            # Get the line data and target point
            line = sel.artist
            xdata, ydata = line.get_data()
            
            # Convert to numpy arrays if they're pandas Series
            if hasattr(xdata, 'values'):
                xdata = xdata.values
            if hasattr(ydata, 'values'):
                ydata = ydata.values
            
            # sel.target contains the (x, y) coordinates
            x_target, y_target = sel.target
            
            # Find the nearest actual data point
            # Convert x_target to index
            if hasattr(sel, 'index') and sel.index is not None:
                # If index is available, use it
                index = int(sel.index) if not isinstance(sel.index, int) else sel.index
            else:
                # Find nearest point manually
                distances = np.abs(xdata - x_target)
                index = np.argmin(distances)
            
            # Make sure index is valid
            if index >= len(xdata):
                index = len(xdata) - 1
            
            # Get the actual data point
            x_val = xdata[index]
            y_val = ydata[index]
            
            # Format the time - check if x_val is already a datetime or a matplotlib date number
            try:
                # If it's a matplotlib date number (float)
                if isinstance(x_val, (int, float, np.floating, np.integer)):
                    time_obj = mdates.num2date(x_val)
                # If it's already a numpy datetime64 or pandas Timestamp
                elif hasattr(x_val, 'strftime'):
                    time_obj = x_val
                else:
                    # Convert numpy datetime64 to pandas Timestamp for strftime
                    time_obj = pd.Timestamp(x_val)
                
                time_str = time_obj.strftime('%H:%M:%S')
            except Exception as e:
                # Fallback - just show the value
                time_str = str(x_val)
            
            # Set the annotation text with actual measured value
            label = line.get_label()
            prefix = f'{label}\n' if label and not label.startswith('_') else ''
            sel.annotation.set_text(f'{prefix}{time_str}\n{y_val:.1f} W')
            sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)
            sel.annotation.arrow_patch.set(arrowstyle='->', lw=1.5)
        
        print("Info: Interactive cursor enabled - hover over curves to see values")
    else:
        print("Info: Install 'mplcursors' for interactive hover tooltips: pip install mplcursors")
    
    plt.show(block=False)

def plot_energy_overview_interactive(df, hours=24):
    """Interactive version of energy overview plot - bar chart with 15-min intervals."""
    if df.empty:
        print(f"No data available.")
        return
    
    latest_time = df['datetime'].max()
    cutoff_time = latest_time - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time].copy()
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    if df_filtered['real_energy_in'].sum() == 0 and df_filtered['real_energy_out'].sum() == 0:
        print("Warning: No energy data available.")
        return
    
    # Calculate energy consumption per 15-minute interval
    df_filtered = df_filtered.sort_values('datetime')
    df_filtered['energy_in_diff'] = df_filtered['real_energy_in'].diff()
    df_filtered['energy_out_diff'] = df_filtered['real_energy_out'].diff()
    
    # Remove negative differences
    df_filtered.loc[df_filtered['energy_in_diff'] < 0, 'energy_in_diff'] = 0
    df_filtered.loc[df_filtered['energy_out_diff'] < 0, 'energy_out_diff'] = 0
    
    # Group by 15-minute intervals
    df_filtered['time_15min'] = df_filtered['datetime'].dt.floor('15min')
    energy_15min = df_filtered.groupby('time_15min').agg({
        'energy_in_diff': 'sum',
        'energy_out_diff': 'sum'
    }).reset_index()
    
    # Convert Wh to kWh
    energy_15min['energy_in_kwh'] = energy_15min['energy_in_diff'] / 1000
    energy_15min['energy_out_kwh'] = energy_15min['energy_out_diff'] / 1000
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Create bar chart
    bar_width = 0.35
    x = range(len(energy_15min))
    
    bars_in = ax.bar([i - bar_width/2 for i in x], energy_15min['energy_in_kwh'], 
                     bar_width, label='Energy In (Consumption)', color='red', alpha=0.7)
    bars_out = ax.bar([i + bar_width/2 for i in x], energy_15min['energy_out_kwh'], 
                      bar_width, label='Energy Out (Feed-in)', color='green', alpha=0.7)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Energy per 15 min (kWh)', fontsize=12)
    ax.set_title(f'Energy Consumption - 15 Min Intervals (Last {hours}h) (INTERACTIVE)', 
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    ax.set_xticks(x)
    labels = [t.strftime('%H:%M') for t in energy_15min['time_15min']]
    ax.set_xticklabels(labels, rotation=45, ha='right')
    
    if len(labels) > 20:
        for i, label in enumerate(ax.xaxis.get_ticklabels()):
            if i % 2 != 0:
                label.set_visible(False)
    
    plt.tight_layout()
    plt.show()

def main():
    """Main function to create all plots."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize Smart Meter Power Data')
    parser.add_argument('--hours', type=float, default=24, 
                       help='Number of hours to plot (default: 24)')
    parser.add_argument('--file', type=str, default=DATA_FILE,
                       help=f'Path to CSV data file (default: {DATA_FILE})')
    parser.add_argument('--tasmota-file', type=str, default=TASMOTA_DATA_FILE,
                       help=f'Path to Tasmota smart-plug CSV file (default: {TASMOTA_DATA_FILE}). '
                            f'Ignored if the file does not exist.')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Show interactive plot instead of saving to file (allows zoom/pan)')
    args = parser.parse_args()
    
    print("Smart Meter Power Data Visualization")
    print("=" * 60)
    
    # Load data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, args.file)
    tasmota_file = os.path.join(script_dir, args.tasmota_file)
    
    print(f"Loading data from: {data_file}")
    df = load_data(data_file)
    print(f"Loaded {len(df)} data points")
    print(f"Time range: {df['datetime'].min()} to {df['datetime'].max()}")
    
    # Print statistics
    print_statistics(df, hours=args.hours)
    
    # Create plots
    if args.interactive:
        print("\nShowing interactive plots...")
        print("\nINTERACTIVE CONTROLS:")
        print("  🏠 Home button  - Reset view (toolbar)")
        print("  ➕ Zoom button  - Click and drag to zoom")
        print("  🖐️  Pan button   - Click and drag to pan")
        print("  Mouse wheel    - Scroll Y-axis")
        print("  Shift+wheel    - Zoom Y-axis")
        print("  Ctrl+wheel     - Zoom X-axis")
        print("  ↑ / ↓ keys     - Scroll Y-axis")
        print("  ← / → keys     - Scroll X-axis (time)")
        print("  + / - keys     - Zoom Y-axis in/out")
        print("  r key          - Reset to original view")
        print()
        # Show interactive plots (don't close, don't save)
        plot_power_overview_interactive(df, hours=args.hours, tasmota_file=tasmota_file)
        plot_energy_overview_interactive(df, hours=args.hours)
    else:
        print("\nGenerating plots...")
    
    # Plot 1: Power overview (Net, In, Out)
    plot_power_overview(df, hours=args.hours, tasmota_file=tasmota_file)
    
    # Plot 2: Energy overview (In, Out)
    plot_energy_overview(df, hours=args.hours)
    
    # Plot 3: Daily summary (only if we have data from multiple days)
    if (df['datetime'].max() - df['datetime'].min()).days >= 1:
        plot_daily_summary(df)
    else:
        print("Skipping daily summary (need data from multiple days)")
    
    print("\nAll plots generated successfully!")
    print(f"Plots saved in: {os.path.join(script_dir, OUTPUT_DIR)}/")

if __name__ == "__main__":
    main()
