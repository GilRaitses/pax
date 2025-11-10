#!/usr/bin/env python3
"""Generate clean Manhattan navigation map"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

fig, ax = plt.subplots(figsize=(12, 10))

# Define Manhattan streets (42nd to 57th)
streets_y = {
    '42nd St': 0,
    '43rd St': 0.5,
    '44th St': 1.0,
    '45th St': 1.5,
    '46th St': 2.0,
    '47th St': 2.5,
    '48th St': 3.0,
    '49th St': 3.5,
    '50th St': 4.0,
    '51st St': 4.5,
    '52nd St': 5.0,
    '53rd St': 5.5,
    '54th St': 6.0,
    '55th St': 6.5,
    '56th St': 7.0,
    '57th St': 7.5
}

# Define avenues (Park to 7th, west to east CORRECTED)
avenues_x = {
    '7th Ave': 0,
    '6th Ave': 1.5,
    '5th Ave': 3.0,
    'Madison Ave': 4.5,
    'Park Ave': 6.0
}

# Draw street grid with light gray
for street, y in streets_y.items():
    ax.plot([min(avenues_x.values()), max(avenues_x.values())], [y, y],
            color='#d8d8d8', linewidth=1.5, alpha=0.6, zorder=1)
    if street in ['42nd St', '45th St', '48th St', '51st St', '54th St', '57th St']:
        ax.text(-0.8, y, street, fontsize=9, va='center', ha='right', color='#666')

for ave, x in avenues_x.items():
    ax.plot([x, x], [min(streets_y.values()), max(streets_y.values())],
            color='#d8d8d8', linewidth=1.5, alpha=0.6, zorder=1)
    ax.text(x, -0.8, ave, fontsize=9, ha='center', va='top', color='#666', rotation=45)

# Positions
gc_x, gc_y = avenues_x['Park Ave'], streets_y['42nd St']
ch_x, ch_y = avenues_x['7th Ave'], streets_y['57th St']

# Draw all intersection nodes
for x in avenues_x.values():
    for y in streets_y.values():
        ax.add_patch(Circle((x, y), 0.08, color='#e8e8f0', ec='#b0b0c0', 
                           linewidth=0.5, zorder=2))

# Route 1: Baseline - East along 42nd, then North on 7th
route1_x = [gc_x, avenues_x['Madison Ave'], avenues_x['5th Ave'], 
            avenues_x['6th Ave'], avenues_x['7th Ave'], ch_x]
route1_y = [gc_y, gc_y, gc_y, gc_y, gc_y, ch_y]
ax.plot(route1_x, route1_y, color='#5dade2', linewidth=5, linestyle='--',
        alpha=0.85, zorder=4, label='Baseline (Manhattan distance)')

# Route 2: Learned heuristic - North on Park, then West on 57th
route2_x = [gc_x, gc_x, ch_x]
route2_y = [gc_y, ch_y, ch_y]
ax.plot(route2_x, route2_y, color='#ec7063', linewidth=5, linestyle='-',
        alpha=0.85, zorder=4, label='Learned heuristic (low stress)')

# Route 3: Alternative - diagonal-ish
route3_x = [gc_x, avenues_x['Madison Ave'], avenues_x['5th Ave'], 
            avenues_x['6th Ave'], ch_x]
route3_y = [gc_y, streets_y['45th St'], streets_y['50th St'], 
            streets_y['54th St'], ch_y]
ax.plot(route3_x, route3_y, color='#af7ac5', linewidth=5, linestyle=':',
        alpha=0.75, zorder=4, label='Alternative path')

# Highlight start and goal with larger markers
ax.add_patch(Circle((gc_x, gc_y), 0.35, color='#52be80', ec='#1e8449',
                   linewidth=3, zorder=6))
ax.text(gc_x, gc_y, 'GC', ha='center', va='center', fontsize=13,
        fontweight='bold', color='white', zorder=7)

ax.add_patch(Circle((ch_x, ch_y), 0.35, color='#ec7063', ec='#c0392b',
                   linewidth=3, zorder=6))
ax.text(ch_x, ch_y, 'CH', ha='center', va='center', fontsize=13,
        fontweight='bold', color='white', zorder=7)

# Add location labels with boxes
ax.text(gc_x, gc_y - 1.0, 'Grand Central\n42nd St & Park Ave', 
        ha='center', va='top', fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                 edgecolor='#52be80', linewidth=2, alpha=0.95))

ax.text(ch_x, ch_y + 1.0, 'Carnegie Hall\n57th St & 7th Ave', 
        ha='center', va='bottom', fontsize=10, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                 edgecolor='#ec7063', linewidth=2, alpha=0.95))

# North arrow
arrow_x, arrow_y = 7.0, 7.0
ax.annotate('', xy=(arrow_x, arrow_y + 0.8), xytext=(arrow_x, arrow_y),
            arrowprops=dict(arrowstyle='->', lw=3, color='#34495e'),
            fontsize=16, fontweight='bold')
ax.text(arrow_x, arrow_y + 1.0, 'N', ha='center', va='bottom',
        fontsize=14, fontweight='bold', color='#34495e')

# Set limits and styling
ax.set_xlim(-1.5, 7.5)
ax.set_ylim(-1.5, 9.0)
ax.set_aspect('equal')
ax.axis('off')

# Title
ax.text(3.0, 8.5, 'Manhattan Navigation: Grand Central to Carnegie Hall', 
        ha='center', fontsize=16, fontweight='bold', color='#2c3e50')
ax.text(3.0, 8.0, 'Midtown Manhattan Street Grid (West ← → East, North ↑)', 
        ha='center', fontsize=12, color='#566573')

# Legend
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3,
         fontsize=11, frameon=True, fancybox=True, shadow=True,
         framealpha=0.95, edgecolor='#bdc3c7')

# Add scale note
ax.text(6.5, -1.2, '~0.8 miles (1.3 km)', ha='right', va='top',
        fontsize=9, style='italic', color='#7f8c8d')

plt.tight_layout()
plt.savefig('manhattan_map.png', dpi=300, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
print("Clean Manhattan map saved to manhattan_map.png")




