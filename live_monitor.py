#!/usr/bin/env python3
"""
Live GUI Monitor for Smart Meter Power Data
Displays real-time power consumption in a continuously updating window.
"""

import pandas as pd
import matplotlib
import os
import sys
import time

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

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta

# Try to import mplcursors for interactive cursor
try:
    import mplcursors
    HAS_MPLCURSORS = True
except ImportError:
    HAS_MPLCURSORS = False

# Configuration
DATA_FILE = "power_data.csv"
UPDATE_INTERVAL = 5000  # Update every 5 seconds (in milliseconds)
DISPLAY_HOURS = 1  # Show last N hours of data
MAX_HISTORY_HOURS = 48  # Max hours of data to keep plotted (for scrolling back)

class LivePowerMonitor:
    def __init__(self, data_file, display_hours=1):
        self.data_file = data_file
        self.display_hours = display_hours
        
        # Create figure and subplots
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(14, 10))
        self.fig.suptitle('Smart Meter - Live Power Monitor', fontsize=16, fontweight='bold')
        
        # Initialize lines for POWER OVERVIEW (all 3 in one graph)
        self.line_net, = self.ax1.plot([], [], 'b-', linewidth=2, label='RealPower (Net)')
        self.line_in, = self.ax1.plot([], [], 'r-', linewidth=1.5, label='RealPowerIn', alpha=0.7)
        self.line_out, = self.ax1.plot([], [], 'g-', linewidth=1.5, label='RealPowerOut', alpha=0.7)
        
        # Energy bars will be created in update_plot
        self.energy_bars_in = None
        self.energy_bars_out = None
        
        # Flag: True once the user manually zooms/scrolls, so auto-scaling stops
        self.user_adjusted_view = False
        # Throttling for keyboard navigation to avoid event backlog / lag
        self._last_key_time = 0.0
        self._key_min_interval = 0.05  # seconds between processed key events
        # Slider widget for horizontal (time) scrolling
        self.time_slider = None
        # Full data range for the slider (set in update_plot)
        self._full_xmin = None
        self._full_xmax = None
        
        # Configure axes
        self.setup_axes()
        
        # Text for statistics
        self.stats_text = self.fig.text(0.02, 0.02, '', fontsize=10, family='monospace',
                                        verticalalignment='bottom')
        
        # Add interactive cursor for power lines if mplcursors is available
        self.cursor = None
        if HAS_MPLCURSORS:
            # Use hover=2 (Transient) to snap to nearest data point
            # This shows tooltips when hovering near the line and snaps to actual measurements
            self.cursor = mplcursors.cursor([self.line_net, self.line_in, self.line_out], hover=2)
            
            @self.cursor.connect("add")
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
                        import pandas as pd
                        time_obj = pd.Timestamp(x_val)
                    
                    time_str = time_obj.strftime('%H:%M:%S')
                except Exception as e:
                    # Fallback - just show the value
                    time_str = str(x_val)
                
                # Set the annotation text with actual measured value
                sel.annotation.set_text(f'{time_str}\n{y_val:.1f} W')
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)
                sel.annotation.arrow_patch.set(arrowstyle='->', lw=1.5)
            
            print("Info: Interactive cursor enabled - hover over power curves to see values")
        else:
            print("Info: Install 'mplcursors' for interactive hover tooltips: pip install mplcursors")
        
    def setup_axes(self):
        """Configure the plot axes."""
        # Power Overview Plot (top) - All 3 power values
        self.ax1.set_ylabel('Power (W)', fontsize=11)
        self.ax1.set_title('Power Overview', fontsize=12)
        # Legend will be set when data is plotted
        self.ax1.grid(True, alpha=0.3)
        self.ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
        
        # Energy Overview Plot (bottom) - Energy per 15min
        self.ax2.set_xlabel('Time', fontsize=11)
        self.ax2.set_ylabel('Energy per 15min (kWh)', fontsize=11)
        self.ax2.set_title('Energy Consumption - 15 Minute Intervals', fontsize=12)
        # Legend will be set when data is plotted
        self.ax2.grid(True, alpha=0.3, axis='y')
        
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
            
            # Ensure energy columns exist and are numeric
            for col in ['real_energy_in', 'real_energy_out']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                else:
                    df[col] = 0
            
            # Drop rows with invalid datetime
            df = df.dropna(subset=['datetime'])
            
            if df.empty:
                return None
            
            # Keep a larger history so the user can scroll back in time.
            # We plot ALL data within MAX_HISTORY_HOURS; the *view* is limited
            # to display_hours (set in update_plot), but scrolling reveals older data.
            latest_time = df['datetime'].max()
            history_cutoff = latest_time - timedelta(hours=MAX_HISTORY_HOURS)
            df = df[df['datetime'] >= history_cutoff]
            
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
            return []
        
        # Update Power Overview plot (top) - All 3 power values in one graph
        self.line_net.set_data(df['datetime'], df['real_power_net'])
        self.line_in.set_data(df['datetime'], df['real_power_in'])
        self.line_out.set_data(df['datetime'], df['real_power_out'])
        
        # Update Energy Overview plot (bottom) - Bar chart with 15-min intervals
        # Clear previous bars
        self.ax2.clear()
        self.setup_axes()  # Re-setup ax2 labels/grid
        
        # Calculate energy per 15-minute interval
        df_sorted = df.sort_values('datetime').copy()
        df_sorted['energy_in_diff'] = df_sorted['real_energy_in'].diff()
        df_sorted['energy_out_diff'] = df_sorted['real_energy_out'].diff()
        
        # Remove negative differences
        df_sorted.loc[df_sorted['energy_in_diff'] < 0, 'energy_in_diff'] = 0
        df_sorted.loc[df_sorted['energy_out_diff'] < 0, 'energy_out_diff'] = 0
        
        # Group by 15-minute intervals
        df_sorted['time_15min'] = df_sorted['datetime'].dt.floor('15min')
        energy_15min = df_sorted.groupby('time_15min').agg({
            'energy_in_diff': 'sum',
            'energy_out_diff': 'sum'
        }).reset_index()
        
        # Convert Wh to kWh
        energy_15min['energy_in_kwh'] = energy_15min['energy_in_diff'] / 1000
        energy_15min['energy_out_kwh'] = energy_15min['energy_out_diff'] / 1000
        
        # Create bar chart
        if not energy_15min.empty:
            bar_width = 0.35
            x = range(len(energy_15min))
            
            self.energy_bars_in = self.ax2.bar([i - bar_width/2 for i in x], 
                                               energy_15min['energy_in_kwh'], 
                                               bar_width, label='Energy In', 
                                               color='red', alpha=0.7)
            self.energy_bars_out = self.ax2.bar([i + bar_width/2 for i in x], 
                                                energy_15min['energy_out_kwh'], 
                                                bar_width, label='Energy Out', 
                                                color='green', alpha=0.7)
            
            # Set x-axis labels
            self.ax2.set_xticks(x)
            labels = [t.strftime('%H:%M') for t in energy_15min['time_15min']]
            self.ax2.set_xticklabels(labels, rotation=45, ha='right')
            
            # Show legend
            self.ax2.legend(loc='upper left')
        
        # Remember the full time range of the plotted data (for the slider)
        self._full_xmin = mdates.date2num(df['datetime'].min())
        self._full_xmax = mdates.date2num(df['datetime'].max())

        # Adjust axes limits (only if user hasn't manually zoomed/scrolled)
        if not self.user_adjusted_view:
            # Default view: show only the last display_hours, but ALL data is
            # plotted so the user can scroll/pan back in time to see older values.
            latest_time = df['datetime'].max()
            view_start = latest_time - timedelta(hours=self.display_hours)
            self.ax1.set_xlim(mdates.date2num(view_start),
                              mdates.date2num(latest_time))

            # Scale Y to the data within the visible (last display_hours) window
            visible = df[df['datetime'] >= view_start]
            if not visible.empty:
                y_vals = pd.concat([
                    visible['real_power_net'],
                    visible['real_power_in'],
                    visible['real_power_out'],
                ])
                ymin = float(y_vals.min())
                ymax = float(y_vals.max())
                margin = (ymax - ymin) * 0.1 if ymax > ymin else 10
                # Don't extend the view below 0 unless the data itself is negative
                lower = ymin - margin
                if ymin >= 0:
                    lower = max(0, lower)
                self.ax1.set_ylim(lower, ymax + margin)

            # Update the slider's valid range to the full data span
            self._update_slider_range()
        
        # Add legends (only if not already present)
        if not self.ax1.get_legend():
            self.ax1.legend(loc='upper left')
        
        # Format x-axis to show time
        date_format = DateFormatter('%H:%M:%S')
        self.ax1.xaxis.set_major_formatter(date_format)
        
        # Rotate labels
        plt.setp(self.ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Update statistics
        self.update_statistics(df)
        
        return []
    
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
    
    def _get_data_yrange(self, ax):
        """Return (data_min, data_max) of all line data currently in the axes.

        Returns (None, None) if there is no plotted data.
        """
        data_min = None
        data_max = None
        for line in ax.get_lines():
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

    def _clamp_ypan(self, ax, new_ymin, new_ymax):
        """Clamp a proposed Y-view so the measurement data always stays visible.

        Prevents panning so far that all curves leave the visible window.
        """
        data_min, data_max = self._get_data_yrange(ax)
        if data_min is None:
            # No data yet - allow the requested range
            return new_ymin, new_ymax

        view_height = new_ymax - new_ymin
        # The visible window must still overlap the data range.
        # Keep at least a small margin of data in view.
        # Lowest allowed bottom: window sits just below data_max
        max_ymin = data_max - view_height * 0.1
        # Highest allowed bottom: window top sits just above data_min
        min_ymin = data_min - view_height * 0.9

        clamped_ymin = max(min_ymin, min(new_ymin, max_ymin))
        # Don't let the view drop below 0 if the data itself is never negative
        if data_min >= 0:
            clamped_ymin = max(0, clamped_ymin)
        clamped_ymax = clamped_ymin + view_height
        return clamped_ymin, clamped_ymax

    def on_scroll(self, event):
        """Handle mouse wheel scrolling for pan/zoom.

        - Mouse wheel:        Scroll Y-axis up/down (pan)
        - Shift + mouse wheel: Zoom Y-axis in/out
        - Ctrl + mouse wheel:  Zoom X-axis in/out
        """
        # Only react if the cursor is inside an axes
        ax = event.inaxes
        if ax is None:
            return

        # Mark that the user has taken control of the view
        self.user_adjusted_view = True

        # event.button is 'up' or 'down'; event.step is +1/-1
        step = event.step  # positive = up/away from user, negative = down/toward user

        # Determine which modifier key is held
        key = event.key  # 'shift', 'control', or None

        if key == 'control':
            # --- Zoom X-axis around the cursor position ---
            xmin, xmax = ax.get_xlim()
            xrange = xmax - xmin
            # Zoom factor: scroll up zooms in (smaller range)
            scale = 0.9 if step > 0 else 1.1
            xdata = event.xdata if event.xdata is not None else (xmin + xmax) / 2
            new_range = xrange * scale
            # Keep cursor position stable
            left_frac = (xdata - xmin) / xrange
            new_xmin = xdata - new_range * left_frac
            new_xmax = xdata + new_range * (1 - left_frac)
            ax.set_xlim(new_xmin, new_xmax)

        elif key == 'shift':
            # --- Zoom Y-axis around the cursor position ---
            ymin, ymax = ax.get_ylim()
            yrange = ymax - ymin
            scale = 0.9 if step > 0 else 1.1
            ydata = event.ydata if event.ydata is not None else (ymin + ymax) / 2
            new_range = yrange * scale
            bottom_frac = (ydata - ymin) / yrange
            new_ymin = ydata - new_range * bottom_frac
            new_ymax = ydata + new_range * (1 - bottom_frac)
            ax.set_ylim(new_ymin, new_ymax)

        else:
            # --- Scroll (pan) Y-axis up/down ---
            ymin, ymax = ax.get_ylim()
            yrange = ymax - ymin
            # Move by 10% of the visible range per scroll step
            shift = yrange * 0.1 * step
            new_ymin, new_ymax = ymin + shift, ymax + shift
            # Clamp so the measurement curves never leave the visible area
            new_ymin, new_ymax = self._clamp_ypan(ax, new_ymin, new_ymax)
            ax.set_ylim(new_ymin, new_ymax)

        # Redraw the canvas to show the change
        self.fig.canvas.draw_idle()

    def on_key(self, event):
        """Handle keyboard arrow keys for scrolling/panning.

        - Up / Down arrows:    Scroll Y-axis up/down
        - Left / Right arrows:  Scroll X-axis (time) left/right
        - '+' / '-':            Zoom Y-axis in/out
        - 'r':                  Reset view (re-enable auto-scaling)
        """
        # Reset view: return control to auto-scaling
        if event.key == 'r':
            self.user_adjusted_view = False
            self.fig.canvas.draw_idle()
            return

        # Only handle navigation keys; ignore everything else early
        if event.key not in ('up', 'down', 'left', 'right', '+', '=', '-'):
            return

        # Throttle: drop key events that arrive faster than we can redraw.
        # This prevents an event backlog that makes the plot keep moving
        # ("running on") after the key is released.
        now = time.monotonic()
        if now - self._last_key_time < self._key_min_interval:
            return
        self._last_key_time = now

        # Use the power axis (ax1) as the target for keyboard navigation
        ax = self.ax1

        # Mark that the user has taken control of the view
        self.user_adjusted_view = True

        if event.key == 'up':
            # Scroll Y-axis up
            ymin, ymax = ax.get_ylim()
            shift = (ymax - ymin) * 0.1
            new_ymin, new_ymax = self._clamp_ypan(ax, ymin + shift, ymax + shift)
            ax.set_ylim(new_ymin, new_ymax)

        elif event.key == 'down':
            # Scroll Y-axis down
            ymin, ymax = ax.get_ylim()
            shift = (ymax - ymin) * 0.1
            new_ymin, new_ymax = self._clamp_ypan(ax, ymin - shift, ymax - shift)
            ax.set_ylim(new_ymin, new_ymax)

        elif event.key == 'right':
            # Scroll X-axis (time) forward
            xmin, xmax = ax.get_xlim()
            shift = (xmax - xmin) * 0.1
            ax.set_xlim(xmin + shift, xmax + shift)
            self._sync_slider(xmin + shift)

        elif event.key == 'left':
            # Scroll X-axis (time) backward
            xmin, xmax = ax.get_xlim()
            shift = (xmax - xmin) * 0.1
            ax.set_xlim(xmin - shift, xmax - shift)
            self._sync_slider(xmin - shift)

        elif event.key in ('+', '='):
            # Zoom Y-axis in
            ymin, ymax = ax.get_ylim()
            center = (ymin + ymax) / 2
            half = (ymax - ymin) / 2 * 0.9
            ax.set_ylim(center - half, center + half)

        elif event.key == '-':
            # Zoom Y-axis out
            ymin, ymax = ax.get_ylim()
            center = (ymin + ymax) / 2
            half = (ymax - ymin) / 2 * 1.1
            ax.set_ylim(center - half, center + half)

        self.fig.canvas.draw_idle()

    def _update_slider_range(self):
        """Update the time slider's min/max to match the full data range."""
        if self.time_slider is None or self._full_xmin is None:
            return
        if self._full_xmax <= self._full_xmin:
            return
        # Adjust the slider's underlying range and current axes position
        self.time_slider.valmin = self._full_xmin
        self.time_slider.valmax = self._full_xmax
        self.time_slider.ax.set_xlim(self._full_xmin, self._full_xmax)
        # Keep the slider handle at the current view start
        xmin, _ = self.ax1.get_xlim()
        val = max(self._full_xmin, min(xmin, self._full_xmax))
        self.time_slider.eventson = False
        self.time_slider.set_val(val)
        self.time_slider.eventson = True

    def _sync_slider(self, new_xmin):
        """Update the time slider position without triggering its callback."""
        if self.time_slider is not None and self._full_xmin is not None:
            # Clamp to valid range
            val = max(self._full_xmin, min(new_xmin, self._full_xmax))
            # eventson=False prevents recursive callback
            self.time_slider.eventson = False
            self.time_slider.set_val(val)
            self.time_slider.eventson = True

    def on_slider_change(self, val):
        """Handle time slider movement: pan the X-axis to the selected start time."""
        if self._full_xmin is None:
            return
        # Current visible width
        xmin, xmax = self.ax1.get_xlim()
        width = xmax - xmin
        # Set new window starting at slider value
        self.user_adjusted_view = True
        self.ax1.set_xlim(val, val + width)
        self.fig.canvas.draw_idle()

    def start(self, interval=UPDATE_INTERVAL):
        """Start the live monitor."""
        # Enable interactive navigation toolbar
        # This provides zoom, pan, and home buttons
        from matplotlib.backend_bases import NavigationToolbar2
        
        ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=interval,
            blit=False,
            cache_frame_data=False
        )
        
        # Enable interactive pan/zoom via mouse wheel
        # Mouse wheel: Scroll Y-axis up/down
        # Shift+wheel: Zoom Y-axis in/out
        # Ctrl+wheel: Zoom X-axis in/out
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        # Enable keyboard arrow-key scrolling
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

        plt.tight_layout()
        # Leave room at the bottom for statistics text AND the time slider
        plt.subplots_adjust(bottom=0.16)

        # --- Create a horizontal scrollbar (Slider) for time navigation ---
        from matplotlib.widgets import Slider
        # Position: [left, bottom, width, height] in figure coordinates
        slider_ax = self.fig.add_axes([0.15, 0.02, 0.70, 0.03])
        # Initial range is a placeholder (0..1); it gets updated once data loads
        self.time_slider = Slider(
            slider_ax, 'Zeit', 0.0, 1.0, valinit=0.0, valstep=None
        )
        self.time_slider.on_changed(self.on_slider_change)
        # Hide the numeric value label (it's a matplotlib date number, not useful)
        self.time_slider.valtext.set_visible(False)
        
        # Show instructions
        print("\n" + "="*70)
        print("INTERACTIVE CONTROLS:")
        print("="*70)
        print("  Toolbar Buttons:")
        print("    🏠 Home     - Reset view to original")
        print("    ⬅️  Back     - Previous view")
        print("    ➡️  Forward  - Next view")
        print("    ➕ Zoom     - Click and drag to zoom into rectangle")
        print("    🖐️  Pan      - Click and drag to move around")
        print("    💾 Save     - Save current view as image")
        print()
        print("  Keyboard/Mouse:")
        print("    Mouse Wheel  - Scroll Y-axis up/down")
        print("    Shift+Wheel  - Zoom in/out on Y-axis")
        print("    Ctrl+Wheel   - Zoom in/out on X-axis")
        print("    'g'          - Toggle grid")
        print("    'l'          - Toggle Y-axis log scale")
        print("="*70)
        print()
        
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
