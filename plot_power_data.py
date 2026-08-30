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
    
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

def plot_realtime_power(df, hours=24):
    """Plot real-time power consumption for the last X hours."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(df_filtered['datetime'], df_filtered['real_power_net'], 
            label='Net Power', linewidth=1.5, color='blue')
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Power (W)', fontsize=12)
    ax.set_title(f'Power Consumption - Last {hours} Hours', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'power_last_{hours}h.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    
    plt.show()

def plot_power_in_out(df, hours=24):
    """Plot power in and power out separately."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # Power In (Consumption)
    ax1.fill_between(df_filtered['datetime'], df_filtered['real_power_in'], 
                     alpha=0.4, color='red', label='Power Consumption')
    ax1.plot(df_filtered['datetime'], df_filtered['real_power_in'], 
            linewidth=1.5, color='darkred')
    ax1.set_ylabel('Power In (W)', fontsize=12)
    ax1.set_title('Power Consumption (from Grid)', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # Power Out (Generation/Feed-in)
    ax2.fill_between(df_filtered['datetime'], df_filtered['real_power_out'], 
                     alpha=0.4, color='green', label='Power Feed-in')
    ax2.plot(df_filtered['datetime'], df_filtered['real_power_out'], 
            linewidth=1.5, color='darkgreen')
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel('Power Out (W)', fontsize=12)
    ax2.set_title('Power Feed-in (to Grid)', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save plot
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f'power_in_out_last_{hours}h.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    
    plt.show()

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
    
    plt.show()

def print_statistics(df, hours=24):
    """Print basic statistics about the power data."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
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
    print(f"{'='*60}\n")

def main():
    """Main function to create all plots."""
    print("Smart Meter Power Data Visualization")
    print("=" * 60)
    
    # Load data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, DATA_FILE)
    
    print(f"Loading data from: {data_file}")
    df = load_data(data_file)
    print(f"Loaded {len(df)} data points")
    print(f"Time range: {df['datetime'].min()} to {df['datetime'].max()}")
    
    # Print statistics
    print_statistics(df, hours=24)
    
    # Create plots
    print("\nGenerating plots...")
    plot_realtime_power(df, hours=24)
    plot_power_in_out(df, hours=24)
    
    # Only create daily summary if we have data from multiple days
    if (df['datetime'].max() - df['datetime'].min()).days >= 1:
        plot_daily_summary(df)
    else:
        print("Skipping daily summary (need data from multiple days)")
    
    print("\nAll plots generated successfully!")

if __name__ == "__main__":
    main()
