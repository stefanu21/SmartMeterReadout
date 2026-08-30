#!/usr/bin/env python3
"""
Simple cursor test - shows if mplcursors is working
Run with: source bin/activate && python3 test_cursor_simple.py
"""
import matplotlib.pyplot as plt
import numpy as np

print("=" * 60)
print("CURSOR TEST")
print("=" * 60)

# Check mplcursors
try:
    import mplcursors
    print("✓ mplcursors is installed:", mplcursors.__version__)
except ImportError:
    print("✗ mplcursors NOT installed!")
    print("  Run: pip install mplcursors")
    exit(1)

# Create simple test data
x = np.linspace(0, 10, 20)
y1 = np.sin(x) * 100 + 1500
y2 = np.cos(x) * 100 + 1500

fig, ax = plt.subplots(figsize=(12, 6))
line1 = ax.plot(x, y1, 'b-o', linewidth=2, markersize=6, label='Line 1')
line2 = ax.plot(x, y2, 'r-o', linewidth=2, markersize=6, label='Line 2')

ax.set_xlabel('X')
ax.set_ylabel('Power (W)')
ax.set_title('CURSOR TEST - Hover over lines/points to see values', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# Add cursor with hover=2 (Transient mode)
cursor = mplcursors.cursor(line1 + line2, hover=2)

@cursor.connect("add")
def on_add(sel):
    line = sel.artist
    xdata, ydata = line.get_data()
    
    # Get target coordinates
    x_target, y_target = sel.target
    
    # Find nearest point
    if hasattr(sel, 'index') and sel.index is not None:
        index = int(sel.index) if not isinstance(sel.index, int) else sel.index
    else:
        distances = np.abs(xdata - x_target)
        index = np.argmin(distances)
    
    if index >= len(xdata):
        index = len(xdata) - 1
    
    x_val = xdata[index]
    y_val = ydata[index]
    
    sel.annotation.set_text(f'X: {x_val:.2f}\nY: {y_val:.1f} W')
    sel.annotation.get_bbox_patch().set(fc="yellow", alpha=0.9)
    sel.annotation.arrow_patch.set(arrowstyle='->', lw=2, color='black')

print("\n" + "=" * 60)
print("TEST INSTRUCTIONS:")
print("=" * 60)
print("1. A window with two curves should appear")
print("2. Move your mouse NEAR or OVER the lines")
print("3. A yellow tooltip should appear showing X and Y values")
print("4. The tooltip should 'snap' to the nearest data point")
print("5. Close the window when done")
print("=" * 60)
print("\nIf you see tooltips -> Cursor is WORKING ✓")
print("If no tooltips appear -> There's a problem ✗")
print("=" * 60 + "\n")

plt.tight_layout()
plt.show()
