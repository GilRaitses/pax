#!/usr/bin/env python3
"""Cinnamoroll-themed process status monitor with ASCII animation.

Features:
- Bouncing Cinnamoroll ASCII art characters
- Large ASCII numbers for counters
- Flipbook animation (updates every 1.5 seconds)
- Cinnamoroll color theme
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ANSI color codes for Cinnamoroll theme
class Colors:
    BLUE = '\033[94m'      # Cinnamoroll Blue
    PINK = '\033[95m'      # Cinnamoroll Pink
    MINT = '\033[96m'      # Cinnamoroll Mint
    CREAM = '\033[97m'     # Cinnamoroll Cream
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CLEAR = '\033[2J\033[H'  # Clear screen and move to top


# ASCII Cinnamoroll frames for animation (bouncing)
# Cinnamoroll is a white dog with floppy ears
CINNAMOROLL_FRAMES = [
    # Frame 1: Normal position (on ground)
    [
        "   ╭───╮",
        "  ( •.• )",
        "   ╰─╯",
        "  ╱   ╲",
        " ╱     ╲",
    ],
    # Frame 2: Slightly up (legs compressed)
    [
        "   ╭───╮",
        "  ( •.• )",
        "   ╰─╯",
        "  ╱   ╲",
        " ╱     ╲",
    ],
    # Frame 3: High bounce (legs extended up)
    [
        "   ╭───╮",
        "  ( •.• )",
        "   ╰─╯",
        "  ╱   ╲",
        " ╱     ╲",
    ],
    # Frame 4: Coming down
    [
        "   ╭───╮",
        "  ( •.• )",
        "   ╰─╯",
        "  ╱   ╲",
        " ╱     ╲",
    ],
    # Frame 5: Landing (squish)
    [
        "   ╭───╮",
        "  ( •.• )",
        "   ╰─╯",
        "  ╱   ╲",
        " ╱     ╲",
    ],
]

# Small ASCII letters (3 rows tall)
SMALL_LETTERS = {
    'I': ["███", " █ ", "███"],
    'M': ["█ █", "███", "█ █"],
    'A': ["███", "█ █", "█ █"],
    'G': ["███", "█  ", "███"],
    'E': ["███", "██ ", "███"],
    'S': ["███", "███", "███"],
    'P': ["███", "█ █", "█  "],
    'R': ["███", "█ █", "█ █"],
    'O': ["███", "█ █", "███"],
    'C': ["███", "█  ", "███"],
    'D': ["██ ", "█ █", "██ "],
    'N': ["█ █", "███", "█ █"],
    'T': ["███", " █ ", " █ "],
    'L': ["█  ", "█  ", "███"],
    'F': ["███", "██ ", "█  "],
    'U': ["█ █", "█ █", "███"],
    'H': ["█ █", "███", "█ █"],
    'Y': ["█ █", " █ ", " █ "],
    'W': ["█ █", "█ █", "███"],
    'V': ["█ █", "█ █", " █ "],
    'X': ["█ █", " █ ", "█ █"],
    'Z': ["███", " █ ", "███"],
    ' ': ["   ", "   ", "   "],
    ':': ["   ", " █ ", "   "],
    '/': ["  █", " █ ", "█  "],
    '%': ["█ █", " █ ", "█ █"],
    '.': ["   ", "   ", " █ "],
    '-': ["   ", "███", "   "],
}

# Large ASCII numbers (5 rows tall)
LARGE_NUMBERS = {
    '0': [
        " ████ ",
        "█    █",
        "█    █",
        "█    █",
        " ████ "
    ],
    '1': [
        "  ██  ",
        " ███  ",
        "  ██  ",
        "  ██  ",
        "██████"
    ],
    '2': [
        " ████ ",
        "    █",
        " ████ ",
        "█     ",
        "██████"
    ],
    '3': [
        " ████ ",
        "    █",
        " ████ ",
        "    █",
        " ████ "
    ],
    '4': [
        "█    █",
        "█    █",
        "██████",
        "    █",
        "    █"
    ],
    '5': [
        "██████",
        "█     ",
        "██████",
        "    █",
        "██████"
    ],
    '6': [
        " ████ ",
        "█     ",
        "██████",
        "█    █",
        " ████ "
    ],
    '7': [
        "██████",
        "    █",
        "   █ ",
        "  █  ",
        " █   "
    ],
    '8': [
        " ████ ",
        "█    █",
        " ████ ",
        "█    █",
        " ████ "
    ],
    '9': [
        " ████ ",
        "█    █",
        " █████",
        "    █",
        " ████ "
    ],
    ':': [
        "     ",
        " ██  ",
        "     ",
        " ██  ",
        "     "
    ],
    '/': [
        "    █",
        "   █ ",
        "  █  ",
        " █   ",
        "█    "
    ],
    '%': [
        "█   █",
        "   █ ",
        "  █  ",
        " █   ",
        "█   █"
    ],
    ' ': [
        "     ",
        "     ",
        "     ",
        "     ",
        "     "
    ],
}

# Large ASCII letters
LARGE_LETTERS = {
    'I': [
        "██████",
        "  ██  ",
        "  ██  ",
        "  ██  ",
        "██████"
    ],
    'M': [
        "█    █",
        "██  ██",
        "█ ██ █",
        "█    █",
        "█    █"
    ],
    'A': [
        " ████ ",
        "█    █",
        "██████",
        "█    █",
        "█    █"
    ],
    'G': [
        " ████ ",
        "█     ",
        "█  ███",
        "█    █",
        " ████ "
    ],
    'E': [
        "██████",
        "█     ",
        "██████",
        "█     ",
        "██████"
    ],
    'S': [
        " ████ ",
        "█     ",
        " ████ ",
        "    █",
        "██████"
    ],
    'P': [
        "██████",
        "█    █",
        "██████",
        "█     ",
        "█     "
    ],
    'R': [
        "██████",
        "█    █",
        "██████",
        "█  █  ",
        "█    █"
    ],
    'O': [
        " ████ ",
        "█    █",
        "█    █",
        "█    █",
        " ████ "
    ],
    'C': [
        " ████ ",
        "█     ",
        "█     ",
        "█     ",
        " ████ "
    ],
    'D': [
        "█████ ",
        "█    █",
        "█    █",
        "█    █",
        "█████ "
    ],
    'N': [
        "█    █",
        "██   █",
        "█ █  █",
        "█  █ █",
        "█   ██"
    ],
    'T': [
        "██████",
        "  ██  ",
        "  ██  ",
        "  ██  ",
        "  ██  "
    ],
    'L': [
        "█     ",
        "█     ",
        "█     ",
        "█     ",
        "██████"
    ],
    'F': [
        "██████",
        "█     ",
        "██████",
        "█     ",
        "█     "
    ],
    'U': [
        "█    █",
        "█    █",
        "█    █",
        "█    █",
        " ████ "
    ],
    'H': [
        "█    █",
        "█    █",
        "██████",
        "█    █",
        "█    █"
    ],
    'Y': [
        "█    █",
        " █  █ ",
        "  ██  ",
        "  ██  ",
        "  ██  "
    ],
    'W': [
        "█    █",
        "█    █",
        "█ ██ █",
        "██  ██",
        "█    █"
    ],
    'V': [
        "█    █",
        "█    █",
        " █  █ ",
        " █  █ ",
        "  ██  "
    ],
    'X': [
        "█    █",
        " █  █ ",
        "  ██  ",
        " █  █ ",
        "█    █"
    ],
    'Z': [
        "██████",
        "   █  ",
        "  █   ",
        " █    ",
        "██████"
    ],
    ' ': [
        "     ",
        "     ",
        "     ",
        "     ",
        "     "
    ],
}


def render_small_text(text: str, color: str = Colors.RESET) -> list[str]:
    """Render text using small ASCII letters (3 rows)."""
    lines = [''] * 3
    for char in text.upper():
        char_lines = SMALL_LETTERS.get(char, SMALL_LETTERS.get(' ', ['   '] * 3))
        for i in range(3):
            lines[i] += char_lines[i] + ' '
    return [color + line + Colors.RESET for line in lines]


def render_large_numbers(text: str, color: str = Colors.RESET) -> list[str]:
    """Render numbers using large ASCII characters (5 rows).
    
    Handles numbers, colons, periods, and dashes by converting small chars to 5-row format.
    """
    lines = [''] * 5
    for char in text:
        if char in LARGE_NUMBERS:
            char_lines = LARGE_NUMBERS[char]
        elif char in SMALL_LETTERS:  # For punctuation/symbols (:, ., -)
            # Convert 3-row to 5-row by centering vertically
            small_lines = SMALL_LETTERS[char]
            char_lines = ['     '] * 5
            # Center the 3-row character in the 5-row space
            char_lines[1] = small_lines[0].center(6)[:6] if len(small_lines[0]) <= 3 else small_lines[0]
            char_lines[2] = small_lines[1].center(6)[:6] if len(small_lines[1]) <= 3 else small_lines[1]
            char_lines[3] = small_lines[2].center(6)[:6] if len(small_lines[2]) <= 3 else small_lines[2]
        else:
            char_lines = ['     '] * 5
        
        for i in range(5):
            lines[i] += char_lines[i] + ' '
    
    return [color + line + Colors.RESET for line in lines]


def render_large_text(text: str, color: str = Colors.RESET) -> list[str]:
    """Render text using large ASCII characters (all 5 rows)."""
    lines = [''] * 5
    for char in text.upper():
        if char in LARGE_LETTERS:
            char_lines = LARGE_LETTERS[char]
        elif char in LARGE_NUMBERS:
            char_lines = LARGE_NUMBERS[char]
        else:
            char_lines = LARGE_LETTERS.get(' ', ['     '] * 5)
        
        for i in range(5):
            lines[i] += char_lines[i] + ' '
    
    return [color + line + Colors.RESET for line in lines]


def get_cinnamoroll_frame(frame_idx: int, x_pos: int, y_pos: int) -> list[str]:
    """Get a Cinnamoroll frame at a specific position."""
    frame = CINNAMOROLL_FRAMES[frame_idx % len(CINNAMOROLL_FRAMES)]
    colored_frame = []
    bounce_frame = frame_idx % len(CINNAMOROLL_FRAMES)
    bounce_offset = abs(bounce_frame - len(CINNAMOROLL_FRAMES) // 2)
    
    for i, line in enumerate(frame):
        # Add horizontal padding for x position
        # Use different colors for different parts
        if i < 2:  # Head/ears
            color = Colors.PINK
        elif i == 2:  # Face
            color = Colors.CREAM
        else:  # Body/legs
            color = Colors.MINT
        
        # Add vertical bounce effect
        vertical_pad = max(0, 2 - bounce_offset) if i == 0 else 0
        padded = ' ' * x_pos + ('\n' * vertical_pad) + color + line + Colors.RESET
        colored_frame.append(padded)
    return colored_frame


def count_local_images(local_dir: Path, date_filter: str | None = None) -> dict:
    """Count images in local directory."""
    if not local_dir.exists():
        return {"total": 0, "by_camera": {}}
    
    total = 0
    by_camera = {}
    
    for img_path in local_dir.rglob("*.jpg"):
        if date_filter:
            filename = img_path.name
            if date_filter not in filename:
                continue
        
        total += 1
        parts = img_path.parts
        if len(parts) >= 2:
            camera_id = parts[-2]
            by_camera[camera_id] = by_camera.get(camera_id, 0) + 1
    
    return {"total": total, "by_camera": by_camera}


def count_features(features_dir: Path) -> int:
    """Count extracted features."""
    if not features_dir.exists():
        return 0
    
    count = 0
    for json_file in features_dir.glob("features_*.json"):
        try:
            import json
            with open(json_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    count += len(data)
                elif isinstance(data, dict):
                    count += len(data.get("features", []))
        except Exception:
            continue
    
    return count


def monitor_process(
    local_dir: Path,
    features_dir: Path | None = None,
    log_file: Path | None = None,
    refresh_interval: float = 1.5,
    date_filter: str | None = None,
):
    """Monitor process with Cinnamoroll animation."""
    if features_dir is None:
        features_dir = Path("data/features")
    
    # Terminal dimensions (will be detected)
    terminal_width = 80
    terminal_height = 24
    
    # Animation state
    frame_idx = 0
    cinnamoroll_x = 5
    cinnamoroll_y = 2
    direction = 1  # 1 = right, -1 = left
    
    # Initial counts
    initial_images = count_local_images(local_dir, date_filter)["total"]
    initial_feature_count = count_features(features_dir)
    
    start_time = time.time()
    last_image_count = initial_images
    last_feature_count = initial_feature_count
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            # Get current counts
            image_stats = count_local_images(local_dir, date_filter)
            current_images = image_stats["total"]
            current_features = count_features(features_dir)
            
            newly_downloaded = current_images - initial_images
            newly_extracted = current_features - initial_feature_count
            
            # Calculate rates
            if elapsed > 0:
                image_rate = newly_downloaded / elapsed
                feature_rate = newly_extracted / elapsed
            else:
                image_rate = 0
                feature_rate = 0
            
            # Update Cinnamoroll position (bounce animation)
            frame_idx += 1
            
            # Calculate bounce height based on frame
            bounce_frame = frame_idx % len(CINNAMOROLL_FRAMES)
            bounce_height = abs(bounce_frame - len(CINNAMOROLL_FRAMES) // 2)
            
            # Move horizontally
            cinnamoroll_x += direction * 2
            
            # Bounce off edges
            if cinnamoroll_x > terminal_width - 20:
                direction = -1
                cinnamoroll_x = terminal_width - 20
            elif cinnamoroll_x < 0:
                direction = 1
                cinnamoroll_x = 0
            
            # Clear screen
            print(Colors.CLEAR, end='')
            
            # Header (simple, no title)
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            print()
            
            # Time
            time_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
            print(Colors.CREAM + f"Time: {time_str}" + Colors.RESET)
            print()
            
            # Elapsed time
            elapsed_label_lines = render_small_text("ELAPSED", Colors.MINT)
            for line in elapsed_label_lines:
                print(line)
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            elapsed_str = f"{elapsed_min:02d}:{elapsed_sec:02d}"
            elapsed_lines = render_large_numbers(elapsed_str, Colors.MINT)
            for line in elapsed_lines:
                print(line)
            print()
            
            # Images counter
            images_label_lines = render_small_text("IMAGES", Colors.PINK)
            for line in images_label_lines:
                print(line)
            # Show newly downloaded, but also show total in small text
            images_str = f"{newly_downloaded}"
            images_lines = render_large_numbers(images_str, Colors.PINK)
            for line in images_lines:
                print(line)
            if current_images > 0:
                total_text = f"(total: {current_images})"
                total_lines = render_small_text(total_text, Colors.CREAM)
                for line in total_lines:
                    print(line)
            print()
            
            # Features counter
            features_label_lines = render_small_text("FEATURES", Colors.MINT)
            for line in features_label_lines:
                print(line)
            features_str = f"{newly_extracted}"
            features_lines = render_large_numbers(features_str, Colors.MINT)
            for line in features_lines:
                print(line)
            if current_features > 0:
                total_text = f"(total: {current_features})"
                total_lines = render_small_text(total_text, Colors.CREAM)
                for line in total_lines:
                    print(line)
            print()
            
            # Rates
            if image_rate > 0:
                rate_label_lines = render_small_text("RATE", Colors.CREAM)
                for line in rate_label_lines:
                    print(line)
                rate_str = f"{image_rate:.1f}"
                rate_lines = render_large_numbers(rate_str, Colors.CREAM)
                for line in rate_lines:
                    print(line)
                print()
            
            # Cinnamoroll animation
            print()
            cinnamoroll_frame = get_cinnamoroll_frame(frame_idx, cinnamoroll_x, cinnamoroll_y)
            for line in cinnamoroll_frame:
                if line.strip():  # Only print non-empty lines
                    print(line)
            
            # Footer
            print()
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            print(Colors.CREAM + "Press Ctrl+C to stop" + Colors.RESET)
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            
            # Check log file if provided
            if log_file and log_file.exists():
                try:
                    with open(log_file) as f:
                        lines = f.readlines()
                        if lines:
                            # Show last 3 lines, wrapping if needed
                            print()
                            print(Colors.CREAM + "Latest log:" + Colors.RESET)
                            # Get last 3 non-empty lines
                            recent_lines = [l.strip() for l in lines[-10:] if l.strip()][-3:]
                            for line in recent_lines:
                                # Wrap long lines
                                if len(line) > terminal_width - 4:
                                    # Split into chunks
                                    chunks = [line[i:i+terminal_width-4] for i in range(0, len(line), terminal_width-4)]
                                    for chunk in chunks:
                                        print(Colors.CREAM + chunk + Colors.RESET)
                                else:
                                    print(Colors.CREAM + line + Colors.RESET)
                except Exception:
                    pass
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n" + Colors.BOLD + Colors.PINK + "Monitoring stopped!" + Colors.RESET)
        print(Colors.CREAM + "Cinnamoroll says goodbye! 👋" + Colors.RESET)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cinnamoroll-themed process monitor with ASCII animation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=Path("data/raw/images"),
        help="Local directory to monitor (default: data/raw/images)",
    )
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=None,
        help="Features directory to monitor (default: data/features)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file to tail (optional)",
    )
    parser.add_argument(
        "--refresh-interval",
        type=float,
        default=1.5,
        help="Refresh interval in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--date-filter",
        type=str,
        help="Date filter (YYYYMMDD) to only count images from this date",
    )
    
    args = parser.parse_args()
    
    monitor_process(
        local_dir=args.local_dir,
        features_dir=args.features_dir,
        log_file=args.log_file,
        refresh_interval=args.refresh_interval,
        date_filter=args.date_filter,
    )


if __name__ == "__main__":
    main()

