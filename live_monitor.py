#!/usr/bin/env python3
"""
Live GUI Monitor for Smart Meter Power Data
Displays real-time power consumption in a continuously updating window.
"""

import pandas as pd
import matplotlib
import os
import sys

# Try different backends in order of preference
# We need to set backend before importing pyplot
backend_set = False
for backend in ['TkAgg', 'Qt5Agg', 'GTK3Agg', 'WXAgg']:
    try:
        matplotlib.use(backend, force=True)
        backend_set = True
        break
    except (ImportError, ModuleNotFoundError):
        continue

if not backend_set:
    # Check if we have a display at all
    if 'DISPLAY' not in os.environ and sys.platform.startswith('linux'):
        print("\nERROR: No display available and no GUI backend found!")
        print("Cannot show live GUI on this system.")
        print("\nPlease use 'plot_power_data.py' to generate static PNG files instead.")
        sys.exit(1)

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta

# Configuration
DATA_FILE = "power_data.csv"
UPDATE_INTERVAL = 5000  # Update every 5 seconds (in milliseconds)
DISPLAY_HOURS = 1  # Show last N hours of data

class LivePowerMonitor:
    def __init__(self, data_file, display_hours=1):
        self.data_file = data_file
        self.display_hours = display_hours
        
        # Create figure and subplots
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
        self.fig.suptitle('Smart Meter - Live Power Monitor', fontsize=16, fontweight='bold')
        
        # Initialize lines
        self.line_net, = self.ax1.plot([], [], 'b-', linewidth=2, label='Net Power')
        self.line_in, = self.ax2.plot([], [], 'r-', linewidth=1.5, label='Power In (Consumption)')
        self.line_out, = self.ax2.plot([], [], 'g-', linewidth=1.5, label='Power Out (Feed-in)')
        
        # Configure axes
        self.setup_axes()
        
        # Text for statistics
        self.stats_text = self.fig.text(0.02, 0.02, '', fontsize=10, family='monospace',
                                        verticalalignment='bottom')
        
    def setup_axes(self):
        """Configure the plot axes."""
        # Net Power Plot (top)
        self.ax1.set_ylabel('Net Power (W)', fontsize=11)
        self.ax1.legend(loc='upper left')
        self.ax1.grid(True, alpha=0.3)
        self.ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
        
        # Power In/Out Plot (bottom)
        self.ax2.set_xlabel('Time', fontsize=11)
        self.ax2.set_ylabel('Power (W)', fontsize=11)
        self.ax2.legend(loc='upper left')
        self.ax2.grid(True, alpha=0.3)
        
    def read_data(self):
        """Read the latest data from CSV file."""
        if not os.path.exists(self.data_file):
            return None
        
        try:
            # Check if file has energy columns
            with open(self.data_file, 'r') as f:
                header = f.readline().strip()
            
            has_energy = 'real_energy_in' in header
            
            # Read CSV - handle potential format issues
            df = pd.read_csv(self.data_file, on_bad_lines='skip')
            if df.empty:
                return None
            
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            
            # Ensure power columns exist and are numeric
            for col in ['real_power_in', 'real_power_out', 'real_power_net']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Drop rows with invalid datetime
            df = df.dropna(subset=['datetime'])
            
            if df.empty:
                return None
            
            # Filter to show only last N hours
            # Use the latest timestamp in the data as reference (not datetime.now())
            latest_time = df['datetime'].max()
            cutoff_time = latest_time - timedelta(hours=self.display_hours)
            df = df[df['datetime'] >= cutoff_time]
            
            return df
        except Exception as e:
            print(f"Error reading data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def update_plot(self, frame):
        """Update the plot with new data."""
        df = self.read_data()
        
        if df is None or df.empty:
            # Show "Waiting for data" message
            self.ax1.clear()
            self.ax2.clear()
            self.setup_axes()
            self.ax1.text(0.5, 0.5, 'Waiting for data...\nMake sure readout-smart-meter.py is running',
                         ha='center', va='center', transform=self.ax1.transAxes,
                         fontsize=14, color='red')
            return self.line_net, self.line_in, self.line_out
        
        # Update Net Power plot
        self.line_net.set_data(df['datetime'], df['real_power_net'])
        
        # Update Power In/Out plot
        self.line_in.set_data(df['datetime'], df['real_power_in'])
        self.line_out.set_data(df['datetime'], df['real_power_out'])
        
        # Adjust axes limits
        self.ax1.relim()
        self.ax1.autoscale_view()
        self.ax2.relim()
        self.ax2.autoscale_view()
        
        # Format x-axis to show time
        date_format = DateFormatter('%H:%M:%S')
        self.ax1.xaxis.set_major_formatter(date_format)
        self.ax2.xaxis.set_major_formatter(date_format)
        
        # Rotate labels
        plt.setp(self.ax1.xaxis.get_majorticklabels(), rotation=45)
        plt.setp(self.ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Update statistics
        self.update_statistics(df)
        
        return self.line_net, self.line_in, self.line_out
    
    def update_statistics(self, df):
        """Update the statistics text."""
        if df is None or df.empty:
            self.stats_text.set_text('')
            return
        
        last_time = df['datetime'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S')
        last_power = df['real_power_net'].iloc[-1]
        avg_power = df['real_power_net'].mean()
        max_power = df['real_power_net'].max()
        min_power = df['real_power_net'].min()
        
        stats = (
            f"Last Update: {last_time}  |  "
            f"Current: {last_power:>6.0f} W  |  "
            f"Avg: {avg_power:>6.0f} W  |  "
            f"Max: {max_power:>6.0f} W  |  "
            f"Min: {min_power:>6.0f} W  |  "
            f"Points: {len(df)}"
        )
        self.stats_text.set_text(stats)
    
    def start(self, interval=UPDATE_INTERVAL):
        """Start the live monitor."""
        ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=interval,
            blit=False,
            cache_frame_data=False
        )
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)  # Make room for statistics
        plt.show()

def main():
    """Main function to start the live monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live GUI Monitor for Smart Meter Data')
    parser.add_argument('--hours', type=float, default=1, 
                       help='Number of hours to display (default: 1)')
    parser.add_argument('--interval', type=int, default=5000,
                       help='Update interval in milliseconds (default: 5000)')
    parser.add_argument('--file', type=str, default=DATA_FILE,
                       help=f'Path to CSV data file (default: {DATA_FILE})')
    args = parser.parse_args()
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, args.file)
    
    print("=" * 70)
    print("Smart Meter Live Monitor")
    print("=" * 70)
    print(f"Data file: {data_file}")
    print(f"Display window: Last {args.hours} hour(s)")
    print(f"Update interval: {args.interval/1000} seconds")
    print("-" * 70)
    print("Starting live monitor...")
    print("Close the window or press Ctrl+C to exit.")
    print("=" * 70)
    
    # Check if display is available
    if 'DISPLAY' not in os.environ and sys.platform.startswith('linux'):
        print("\nWARNING: No DISPLAY environment variable found!")
        print("The GUI cannot be shown without a graphical environment.")
        print("")
        print("Options:")
        print("  1. Run on a system with desktop environment")
        print("  2. Use X11 forwarding: ssh -X user@host")
        print("  3. Use VNC or other remote desktop")
        print("  4. Use plot_power_data.py to generate static PNG files instead")
        sys.exit(1)
    
    try:
        monitor = LivePowerMonitor(data_file, display_hours=args.hours)
        monitor.start(interval=args.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting GUI: {e}")
        print("\nIf you see display-related errors, the GUI cannot run without")
        print("a graphical environment. Use plot_power_data.py instead to")
        print("generate static plots.")
        sys.exit(1)

if __name__ == "__main__":
    main()
