#!/usr/bin/env python3
"""
Demo script to test the live monitor with simulated data.
Creates sample power data and launches the GUI.
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta
import subprocess

DATA_FILE = "power_data_demo.csv"

def generate_demo_data(minutes=60):
    """Generate demo power data for testing."""
    print(f"Generating {minutes} minutes of demo data...")
    
    with open(DATA_FILE, "w") as f:
        # Write header
        f.write("timestamp,datetime,real_power_in,real_power_out,real_power_net\n")
        
        # Generate data points (one every 5 seconds)
        now = datetime.now()
        start_time = now - timedelta(minutes=minutes)
        
        for i in range(0, minutes * 12):  # 12 data points per minute
            timestamp = start_time + timedelta(seconds=i*5)
            ts = int(timestamp.timestamp())
            dt_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Simulate realistic power consumption pattern
            hour = timestamp.hour
            
            # Base load + time-dependent consumption
            if 6 <= hour < 9:  # Morning peak
                base = 1500 + random.randint(-200, 500)
            elif 11 <= hour < 13:  # Midday
                base = 800 + random.randint(-300, 300)
            elif 17 <= hour < 21:  # Evening peak
                base = 2000 + random.randint(-300, 800)
            elif 22 <= hour or hour < 6:  # Night
                base = 300 + random.randint(-100, 200)
            else:
                base = 1000 + random.randint(-300, 400)
            
            # Simulate solar generation (if during day)
            if 7 <= hour < 19:
                # Peak generation around noon
                solar_factor = 1 - abs(hour - 13) / 6
                power_out = int(solar_factor * (2000 + random.randint(-500, 500)))
            else:
                power_out = 0
            
            power_in = max(0, base - power_out)
            power_net = power_in - power_out
            
            f.write(f"{ts},{dt_str},{power_in},{power_out},{power_net}\n")
    
    print(f"✓ Demo data written to {DATA_FILE}")
    return DATA_FILE

def main():
    print("=" * 70)
    print("Live Monitor Demo - Simulated Smart Meter Data")
    print("=" * 70)
    
    # Generate demo data
    demo_file = generate_demo_data(minutes=60)
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monitor_script = os.path.join(script_dir, "live_monitor.py")
    
    if not os.path.exists(monitor_script):
        print(f"Error: live_monitor.py not found at {monitor_script}")
        sys.exit(1)
    
    print("\nStarting live monitor with demo data...")
    print("(The demo data shows last 60 minutes)")
    print("-" * 70)
    print("Close the GUI window to exit.")
    print("=" * 70)
    
    # Launch the monitor
    try:
        subprocess.run([
            sys.executable,
            monitor_script,
            "--file", demo_file,
            "--hours", "1"
        ])
    except KeyboardInterrupt:
        print("\nDemo stopped by user.")
    
    # Cleanup
    print("\nDemo finished.")
    if os.path.exists(demo_file):
        try:
            os.remove(demo_file)
            print(f"Cleaned up demo file: {demo_file}")
        except:
            print(f"Note: You may want to delete {demo_file} manually.")

if __name__ == "__main__":
    main()
