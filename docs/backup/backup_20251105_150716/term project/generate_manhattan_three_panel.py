#!/usr/bin/env python3
"""Generate Manhattan navigation map with 3 separate panels (like prog02)"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch

# Create figure with 3 subplots side by side - MUCH LARGER
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 10))

# Define Manhattan streets (42nd to 57th) - Y axis, North is UP
streets_y = {
    '42nd': 0, '45th': 1.5, '48th': 3.0,
    '51st': 4.5, '54th': 6.0, '57th': 7.5
}

# Define avenues - X axis, WEST (7th) on LEFT, EAST (Park) on RIGHT
avenues_x = {
    '7th': 0,      # WEST
    '6th': 1.5,
    '5th': 3.0,
    'Madison': 4.5,
    'Park': 6.0    # EAST
}

# All streets for grid
all_streets_y = {f'{i}': (i-42)*0.5 for i in range(42, 58)}
all_avenues_x = {'7th': 0, '6th': 1.5, '5th': 3.0, 'Madison': 4.5, 'Park': 6.0}

# Positions
gc_x, gc_y = avenues_x['Park'], streets_y['42nd']  # EAST, SOUTH
ch_x, ch_y = avenues_x['7th'], streets_y['57th']   # WEST, NORTH

def draw_base_map(ax):
    """Draw the base street grid"""
    # Draw street grid (horizontal lines)
    for y in all_streets_y.values():
        ax.plot([0, 6.0], [y, y], color='#e0e0e0', linewidth=1.5, alpha=0.7, zorder=1)
    
    # Draw avenue grid (vertical lines)
    for x in all_avenues_x.values():
        ax.plot([x, x], [0, 7.5], color='#e0e0e0', linewidth=1.5, alpha=0.7, zorder=1)
    
    # Draw intersection nodes
    for x in all_avenues_x.values():
        for y in all_streets_y.values():
            ax.add_patch(Circle((x, y), 0.08, color='#f0f0f0', 
                               ec='#c0c0c0', linewidth=0.8, zorder=2))
    
    # Label major streets (LEFT side) - Streets run EAST-WEST
    for street, y in streets_y.items():
        ax.text(-0.7, y, street, fontsize=11, 
               va='center', ha='right', color='#444', fontweight='bold')
    
    # Label avenues (BOTTOM) - Avenues run NORTH-SOUTH
    for ave, x in avenues_x.items():
        ax.text(x, -0.8, ave, fontsize=11, 
               ha='center', va='top', color='#444', fontweight='bold', rotation=0)
    
    # Start marker (GC) - Southeast corner
    ax.add_patch(Circle((gc_x, gc_y), 0.30, color='#52be80', 
                       ec='#1e8449', linewidth=3, zorder=6))
    ax.text(gc_x, gc_y, 'GC', ha='center', va='center', 
           fontsize=14, fontweight='bold', color='white', zorder=7)
    
    # Goal marker (CH) - Northwest corner
    ax.add_patch(Circle((ch_x, ch_y), 0.30, color='#ec7063',
                       ec='#c0392b', linewidth=3, zorder=6))
    ax.text(ch_x, ch_y, 'CH', ha='center', va='center',
           fontsize=14, fontweight='bold', color='white', zorder=7)
    
    # Add NORTH arrow
    ax.annotate('', xy=(6.8, 7.2), xytext=(6.8, 6.5),
                arrowprops=dict(arrowstyle='->', lw=3, color='#2c3e50'))
    ax.text(6.8, 7.4, 'N', ha='center', va='bottom',
           fontsize=16, fontweight='bold', color='#2c3e50')
    
    # Add WEST and EAST labels
    ax.text(-0.5, 8.5, 'WEST', ha='center', fontsize=12, 
           fontweight='bold', color='#7f8c8d', style='italic')
    ax.text(6.0, 8.5, 'EAST', ha='center', fontsize=12,
           fontweight='bold', color='#7f8c8d', style='italic')
    
    ax.set_xlim(-1.5, 7.5)
    ax.set_ylim(-1.5, 9.0)
    ax.set_aspect('equal')
    ax.axis('off')

# Panel 1: Baseline (Manhattan distance) - WEST on 42nd, then NORTH on 7th
draw_base_map(ax1)
route1_x = [gc_x, 4.5, 3.0, 1.5, 0]  # Go WEST across 42nd
route1_y = [gc_y, gc_y, gc_y, gc_y, gc_y]
ax1.plot(route1_x, route1_y, color='#5dade2', linewidth=6, 
        linestyle='--', alpha=0.9, zorder=4)
route1b_x = [0, ch_x]  # Then NORTH on 7th
route1b_y = [gc_y, ch_y]
ax1.plot(route1b_x, route1b_y, color='#5dade2', linewidth=6,
        linestyle='--', alpha=0.9, zorder=4)
ax1.set_title('Baseline (Manhattan Distance)\nWest on 42nd → North on 7th', 
             fontsize=14, fontweight='bold', color='#2c3e50', pad=20)

# Panel 2: Learned heuristic - NORTH on Park, then WEST on 57th
draw_base_map(ax2)
route2_x = [gc_x, gc_x]  # Go NORTH on Park
route2_y = [gc_y, ch_y]
ax2.plot(route2_x, route2_y, color='#ec7063', linewidth=6,
        linestyle='-', alpha=0.9, zorder=4)
route2b_x = [gc_x, ch_x]  # Then WEST on 57th
route2b_y = [ch_y, ch_y]
ax2.plot(route2b_x, route2b_y, color='#ec7063', linewidth=6,
        linestyle='-', alpha=0.9, zorder=4)
ax2.set_title('Learned Heuristic (Low Stress)\nNorth on Park → West on 57th',
             fontsize=14, fontweight='bold', color='#2c3e50', pad=20)

# Panel 3: Alternative path - diagonal through midtown
draw_base_map(ax3)
route3_x = [gc_x, 4.5, 3.0, 1.5, ch_x]
route3_y = [gc_y, 1.5, 3.0, 5.0, ch_y]
ax3.plot(route3_x, route3_y, color='#af7ac5', linewidth=6,
        linestyle=':', alpha=0.9, zorder=4)
ax3.set_title('Alternative Mixed Path\nDiagonal through Midtown',
             fontsize=14, fontweight='bold', color='#2c3e50', pad=20)

# Add overall title at top with more space
fig.suptitle('Manhattan Navigation: Grand Central to Carnegie Hall\nRoute Comparison',
            fontsize=18, fontweight='bold', y=0.96)

# Add note at bottom with proper spacing
fig.text(0.5, 0.02, 'GC = Grand Central (42nd St & Park Ave, Southeast) | CH = Carnegie Hall (57th St & 7th Ave, Northwest) | ~0.8 miles',
        ha='center', fontsize=12, color='#555', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.94])
plt.savefig('manhattan_map.png', dpi=300, bbox_inches='tight',
           facecolor='white', edgecolor='none', pad_inches=0.5)
print("Three-panel Manhattan map saved to manhattan_map.png")
