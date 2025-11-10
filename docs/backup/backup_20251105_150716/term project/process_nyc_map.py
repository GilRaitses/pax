#!/usr/bin/env python3
"""Process NYC DOT map screenshot - rotate and crop to align Manhattan grid"""

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.patches import Circle, FancyArrowPatch
import sys

# Check if image file exists
import os
image_files = [f for f in os.listdir('.') if f.endswith(('.png', '.jpg', '.jpeg')) and 'nyc' in f.lower() or 'map' in f.lower() or 'screenshot' in f.lower()]

if not image_files:
    print("Please save one of the NYC DOT map screenshots to this folder first.")
    print("Name it something like 'nyc_map_screenshot.png'")
    sys.exit(1)

# Use the first matching file
input_file = image_files[0]
print(f"Processing: {input_file}")

# Load image
img = Image.open(input_file)
img_array = np.array(img)

# Rotate to align Manhattan grid with edges (Manhattan is rotated ~29 degrees)
# Rotate counterclockwise to align
img_rotated = img.rotate(29, expand=True, fillcolor=(255, 255, 255))

# Create figure
fig, ax = plt.subplots(figsize=(14, 10))

# Display rotated image
ax.imshow(img_rotated, aspect='auto')

# Get image dimensions to calculate positions
h, w = np.array(img_rotated).shape[:2]

# Estimate positions for Grand Central and Carnegie Hall
# These are rough estimates - adjust based on actual image
gc_x, gc_y = w * 0.75, h * 0.85  # Grand Central (southeast area)
ch_x, ch_y = w * 0.25, h * 0.15  # Carnegie Hall (northwest area)

# Add markers
# Start marker
circle_gc = Circle((gc_x, gc_y), radius=30, color='#52be80', ec='#1e8449', 
                   linewidth=4, zorder=10, alpha=0.9)
ax.add_patch(circle_gc)
ax.text(gc_x, gc_y, 'GC', ha='center', va='center', 
       fontsize=16, fontweight='bold', color='white', zorder=11)
ax.text(gc_x, gc_y + 60, 'Grand Central\n42nd & Park', ha='center', va='top',
       fontsize=12, fontweight='bold', color='#1e8449',
       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='#1e8449', linewidth=2))

# Goal marker
circle_ch = Circle((ch_x, ch_y), radius=30, color='#ec7063', ec='#c0392b',
                   linewidth=4, zorder=10, alpha=0.9)
ax.add_patch(circle_ch)
ax.text(ch_x, ch_y, 'CH', ha='center', va='center',
       fontsize=16, fontweight='bold', color='white', zorder=11)
ax.text(ch_x, ch_y - 60, 'Carnegie Hall\n57th & 7th', ha='center', va='bottom',
       fontsize=12, fontweight='bold', color='#c0392b',
       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='#c0392b', linewidth=2))

# Draw route paths
# Route 1: Baseline (blue dashed)
route1_x = [gc_x, gc_x - w*0.15, gc_x - w*0.30, gc_x - w*0.45, ch_x, ch_x]
route1_y = [gc_y, gc_y, gc_y, gc_y, gc_y, ch_y]
ax.plot(route1_x, route1_y, color='#5dade2', linewidth=6, linestyle='--',
       alpha=0.8, zorder=5, label='Baseline (Manhattan)')

# Route 2: Learned (pink solid)
route2_x = [gc_x, gc_x, ch_x]
route2_y = [gc_y, ch_y, ch_y]
ax.plot(route2_x, route2_y, color='#ec7063', linewidth=6, linestyle='-',
       alpha=0.8, zorder=5, label='Learned heuristic')

# Route 3: Alternative (purple dotted)
route3_x = [gc_x, gc_x - w*0.10, gc_x - w*0.10, gc_x - w*0.25, gc_x - w*0.25, gc_x - w*0.40, gc_x - w*0.40, ch_x]
route3_y = [gc_y, gc_y, gc_y - h*0.15, gc_y - h*0.15, gc_y - h*0.35, gc_y - h*0.35, gc_y - h*0.55, ch_y]
ax.plot(route3_x, route3_y, color='#af7ac5', linewidth=6, linestyle=':',
       alpha=0.8, zorder=5, label='Alternative path')

# North arrow
arrow_x, arrow_y = w * 0.92, h * 0.15
ax.annotate('', xy=(arrow_x, arrow_y - 50), xytext=(arrow_x, arrow_y),
           arrowprops=dict(arrowstyle='->', lw=4, color='#2c3e50'))
ax.text(arrow_x, arrow_y - 70, 'N', ha='center', va='top',
       fontsize=18, fontweight='bold', color='#2c3e50')

# Add title
ax.text(w/2, -50, 'Manhattan Navigation: Grand Central to Carnegie Hall\nNYC DOT Traffic Camera Network',
       ha='center', va='bottom', fontsize=16, fontweight='bold', color='#2c3e50')

# Legend
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.08), ncol=3,
         fontsize=12, frameon=True, fancybox=True, framealpha=0.95)

ax.axis('off')

plt.tight_layout()
plt.savefig('manhattan_map.png', dpi=300, bbox_inches='tight',
           facecolor='white', pad_inches=0.3)
print("Processed map saved to manhattan_map.png")
print("Note: You may need to adjust the position estimates (gc_x, gc_y, ch_x, ch_y) to match actual locations in your screenshot")




