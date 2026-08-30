#!/usr/bin/env python3
"""
Script to visualize power consumption data from smart meter.
Reads power_data.csv and creates various plots.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import sys
import os

# Configuration
DATA_FILE = "power_data.csv"
OUTPUT_DIR = "plots"

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

def plot_power_overview(df, hours=24):
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
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Power (W)', fontsize=12)
    ax.set_title(f'Power Overview - Last {hours} Hours', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
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

def plot_power_overview_interactive(df, hours=24):
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
    
    ax.plot(df_filtered['datetime'], df_filtered['real_power_net'], 
            label='RealPower (Net)', linewidth=2, color='blue')
    ax.plot(df_filtered['datetime'], df_filtered['real_power_in'], 
            label='RealPowerIn (Consumption)', linewidth=1.5, color='red', alpha=0.7)
    ax.plot(df_filtered['datetime'], df_filtered['real_power_out'], 
            label='RealPowerOut (Feed-in)', linewidth=1.5, color='green', alpha=0.7)
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Power (W)', fontsize=12)
    ax.set_title(f'Power Overview - Last {hours} Hours (INTERACTIVE)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
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
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Show interactive plot instead of saving to file (allows zoom/pan)')
    args = parser.parse_args()
    
    print("Smart Meter Power Data Visualization")
    print("=" * 60)
    
    # Load data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, args.file)
    
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
        print("  🏠 Home button  - Reset view")
        print("  ➕ Zoom button  - Click and drag to zoom")
        print("  🖐️  Pan button   - Click and drag to pan")
        print("  Mouse wheel    - Scroll Y-axis")
        print("  Shift+wheel    - Zoom Y-axis")
        print("  Ctrl+wheel     - Zoom X-axis")
        print()
        # Show interactive plots (don't close, don't save)
        plot_power_overview_interactive(df, hours=args.hours)
        plot_energy_overview_interactive(df, hours=args.hours)
    else:
        print("\nGenerating plots...")
    
    # Plot 1: Power overview (Net, In, Out)
    plot_power_overview(df, hours=args.hours)
    
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
