#!/bin/bash
# Process screenshots from Desktop

cd "/Users/gilraitses/cis667/term project"

python3 << 'PYTHON_EOF'
from PIL import Image
import os

screenshots = [
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.40.42 PM.png',
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.34.10 PM.png',
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.39.53 PM.png',
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.40.07 PM.png',
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.40.17 PM.png',
    '/Users/gilraitses/Desktop/Screenshot 2025-11-01 at 8.40.31 PM.png'
]

print("Processing screenshots from Desktop...\n")
for i, f in enumerate(screenshots, 1):
    if os.path.exists(f):
        img = Image.open(f)
        print(f"Screenshot {i}: {img.size[0]}x{img.size[1]} - {os.path.basename(f)}")
        
        # Rotate 29 degrees counterclockwise to align Manhattan grid with figure edges
        img_rotated = img.rotate(29, expand=True, fillcolor=(255, 255, 255))
        
        # Crop
        width, height = img_rotated.size
        left = int(width * 0.08)
        top = int(height * 0.08)
        right = int(width * 0.92)
        bottom = int(height * 0.92)
        img_cropped = img_rotated.crop((left, top, right, bottom))
        
        # Save to term project folder
        output = f'manhattan_screenshot_{i}.png'
        img_cropped.save(output)
        print(f"  Saved: {output} ({img_cropped.size[0]}x{img_cropped.size[1]})\n")

print("="*70)
print("All screenshots processed! Use the one that best shows the")
print("Grand Central (42nd & Park) to Carnegie Hall (57th & 7th) area.")
print("="*70)
PYTHON_EOF




