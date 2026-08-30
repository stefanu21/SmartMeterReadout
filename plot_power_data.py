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
    
    # Check if energy columns exist (for backward compatibility)
    if 'real_energy_in' not in df.columns:
        print("Warning: Energy data not found in CSV. Only power data will be plotted.")
        df['real_energy_in'] = 0
        df['real_energy_out'] = 0
    
    return df

def plot_power_overview(df, hours=24):
    """Plot RealPower (net), RealPowerIn and RealPowerOut in one graph."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
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
    """Plot RealEnergyIn and RealEnergyOut in one graph."""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    df_filtered = df[df['datetime'] >= cutoff_time]
    
    if df_filtered.empty:
        print(f"No data available for the last {hours} hours.")
        return
    
    # Check if energy data exists
    if df_filtered['real_energy_in'].sum() == 0 and df_filtered['real_energy_out'].sum() == 0:
        print("Warning: No energy data available. Skipping energy plot.")
        return
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Convert Wh to kWh for better readability
    energy_in_kwh = df_filtered['real_energy_in'] / 1000
    energy_out_kwh = df_filtered['real_energy_out'] / 1000
    
    # Plot both energy values
    ax.plot(df_filtered['datetime'], energy_in_kwh, 
            label='RealEnergyIn (Consumed)', linewidth=2, color='red')
    ax.plot(df_filtered['datetime'], energy_out_kwh, 
            label='RealEnergyOut (Fed-in)', linewidth=2, color='green')
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Energy (kWh)', fontsize=12)
    ax.set_title(f'Energy Counters - Last {hours} Hours', fontsize=14, fontweight='bold')
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

def main():
    """Main function to create all plots."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visualize Smart Meter Power Data')
    parser.add_argument('--hours', type=float, default=24, 
                       help='Number of hours to plot (default: 24)')
    parser.add_argument('--file', type=str, default=DATA_FILE,
                       help=f'Path to CSV data file (default: {DATA_FILE})')
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
