#!/usr/bin/env python3
"""Process NYC DOT map screenshots - rotate, crop, and annotate"""

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import os

# Find all screenshots
screenshots = [
    'Screenshot 2025-11-01 at 8.39.53 PM.png',
    'Screenshot 2025-11-01 at 8.40.07 PM.png',
    'Screenshot 2025-11-01 at 8.40.17 PM.png',
    'Screenshot 2025-11-01 at 8.40.31 PM.png',
    'Screenshot 2025-11-01 at 8.40.42 PM.png'
]

# Process each to preview
for i, screenshot in enumerate(screenshots):
    if os.path.exists(screenshot):
        print(f"\nProcessing screenshot {i+1}: {screenshot}")
        
        # Load image
        img = Image.open(screenshot)
        
        print(f"  Original size: {img.size[0]} x {img.size[1]}")
        
        # Rotate to align Manhattan grid (Manhattan's grid is ~29° from true north)
        img_rotated = img.rotate(29, expand=True, fillcolor=(255, 255, 255))
        
        # Save rotated and cropped version
        width, height = img_rotated.size
        
        # Crop to focus on central area
        left = width * 0.10
        top = height * 0.10
        right = width * 0.90
        bottom = height * 0.90
        
        img_cropped = img_rotated.crop((int(left), int(top), int(right), int(bottom)))
        
        # Save preview
        output_name = f'processed_screenshot_{i+1}.png'
        img_cropped.save(output_name, dpi=(300, 300))
        print(f"  Saved to: {output_name}")
        print(f"  New size: {img_cropped.size[0]} x {img_cropped.size[1]}")
    else:
        print(f"\nSkipping (not found): {screenshot}")

print("\n" + "="*70)
print("Processed images saved. Review them to find the best one showing")
print("the area between 42nd St (Grand Central) and 57th St (Carnegie Hall).")
print("="*70)
