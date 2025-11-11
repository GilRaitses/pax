#!/usr/bin/env python3
"""Bubble-themed process status monitor with floating bubble animation.

Features:
- Floating bubbles of different sizes
- Bubbles float, grow, shrink, rotate, and revolve
- Max 3 bubbles per size category
- Bubbles pop when progress percentage changes
- Normal-sized text for stats
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ANSI color codes for bubble theme
class Colors:
    BLUE = '\033[94m'      # Light blue
    PINK = '\033[95m'      # Pink
    MINT = '\033[96m'     # Mint
    CREAM = '\033[97m'    # Cream
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CLEAR = '\033[2J\033[H'  # Clear screen and move to top


@dataclass
class Bubble:
    """A floating bubble with physics."""
    x: float
    y: float
    size: float  # Base size
    current_size: float  # Current size (for growth/shrink)
    vx: float  # Horizontal velocity
    vy: float  # Vertical velocity
    rotation: float  # Rotation angle
    rotation_speed: float  # Rotation speed
    growth_phase: float  # Growth phase (0-2π)
    growth_speed: float  # Growth speed
    orbit_center_x: float  # Orbit center X
    orbit_center_y: float  # Orbit center Y
    orbit_radius: float  # Orbit radius
    orbit_angle: float  # Orbit angle
    orbit_speed: float  # Orbit speed
    spawn_time: float  # When bubble was spawned
    color: str  # Bubble color
    
    def update(self, dt: float, terminal_width: int, terminal_height: int):
        """Update bubble physics."""
        # Update orbit
        if self.orbit_radius > 0:
            self.orbit_angle += self.orbit_speed * dt
            self.x = self.orbit_center_x + math.cos(self.orbit_angle) * self.orbit_radius
            self.y = self.orbit_center_y + math.sin(self.orbit_angle) * self.orbit_radius
        
        # Update position with velocity
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Bounce off edges
        if self.x < self.current_size:
            self.x = self.current_size
            self.vx = abs(self.vx)
        elif self.x > terminal_width - self.current_size:
            self.x = terminal_width - self.current_size
            self.vx = -abs(self.vx)
        
        if self.y < self.current_size:
            self.y = self.current_size
            self.vy = abs(self.vy)
        elif self.y > terminal_height - self.current_size:
            self.y = terminal_height - self.current_size
            self.vy = -abs(self.vy)
        
        # Update rotation
        self.rotation += self.rotation_speed * dt
        
        # Update growth (shapeshifting)
        self.growth_phase += self.growth_speed * dt
        growth_factor = 1.0 + 0.2 * math.sin(self.growth_phase)  # ±20% size variation
        self.current_size = self.size * growth_factor
        
        # Gentle floating (slight vertical drift)
        self.vy += math.sin(time.time() * 0.5) * 0.1 * dt
    
    def get_char(self, dx: int, dy: int) -> str:
        """Get character at offset from bubble center."""
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > self.current_size:
            return ' '
        
        # Create bubble shape with rotation
        angle = math.atan2(dy, dx) - self.rotation
        # Use distance to create circular shape
        edge_dist = abs(dist - self.current_size)
        
        if edge_dist < 0.5:
            return '○'  # Edge
        elif edge_dist < 1.0:
            return '◉'  # Near edge
        elif dist < self.current_size * 0.7:
            return '◯'  # Middle
        else:
            return ' '


class BubbleSystem:
    """Manages bubbles and their lifecycle."""
    
    def __init__(self, terminal_width: int, terminal_height: int):
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height
        self.bubbles: list[Bubble] = []
        self.size_categories = {
            'small': (2.0, 3.0),   # Size range
            'medium': (4.0, 6.0),
            'large': (7.0, 10.0),
        }
        self.max_per_size = 3
        self.min_lifetime = 60.0  # 1 minute minimum
        self.current_progress = 0.0
        self.last_progress_change = time.time()
    
    def spawn_bubble(self, size_category: str):
        """Spawn a new bubble of given size category."""
        size_min, size_max = self.size_categories[size_category]
        
        # Count existing bubbles of this size
        count = sum(1 for b in self.bubbles if size_min <= b.size <= size_max)
        if count >= self.max_per_size:
            return
        
        # Random size within category
        size = random.uniform(size_min, size_max)
        
        # Random position
        x = random.uniform(size, self.terminal_width - size)
        y = random.uniform(size, self.terminal_height - size)
        
        # Random velocity (gentle floating)
        vx = random.uniform(-0.5, 0.5)
        vy = random.uniform(-0.3, 0.3)
        
        # Random rotation
        rotation = random.uniform(0, 2 * math.pi)
        rotation_speed = random.uniform(-0.5, 0.5)
        
        # Growth animation
        growth_phase = random.uniform(0, 2 * math.pi)
        growth_speed = random.uniform(0.3, 0.8)
        
        # Orbit (some bubbles orbit around others)
        orbit_radius = random.uniform(0, 8) if random.random() < 0.3 else 0
        orbit_angle = random.uniform(0, 2 * math.pi)
        orbit_speed = random.uniform(0.2, 0.5) if orbit_radius > 0 else 0
        
        # Orbit center (if orbiting, use another bubble or random point)
        if orbit_radius > 0 and self.bubbles:
            center_bubble = random.choice(self.bubbles)
            orbit_center_x = center_bubble.x
            orbit_center_y = center_bubble.y
        else:
            orbit_center_x = x
            orbit_center_y = y
        
        # Random color
        colors = [Colors.BLUE, Colors.PINK, Colors.MINT, Colors.CREAM]
        color = random.choice(colors)
        
        bubble = Bubble(
            x=x, y=y,
            size=size, current_size=size,
            vx=vx, vy=vy,
            rotation=rotation, rotation_speed=rotation_speed,
            growth_phase=growth_phase, growth_speed=growth_speed,
            orbit_center_x=orbit_center_x,
            orbit_center_y=orbit_center_y,
            orbit_radius=orbit_radius,
            orbit_angle=orbit_angle,
            orbit_speed=orbit_speed,
            spawn_time=time.time(),
            color=color,
        )
        
        self.bubbles.append(bubble)
    
    def update(self, dt: float, progress: float):
        """Update all bubbles and handle progress changes."""
        # Check if progress changed
        if abs(progress - self.current_progress) > 0.01:  # 1% threshold
            # Pop all bubbles if they've lived at least 1 minute
            current_time = time.time()
            self.bubbles = [
                b for b in self.bubbles
                if (current_time - b.spawn_time) < self.min_lifetime
            ]
            self.current_progress = progress
            self.last_progress_change = current_time
        
        # Update all bubbles
        for bubble in self.bubbles:
            bubble.update(dt, self.terminal_width, self.terminal_height)
        
        # Spawn new bubbles to maintain population
        for category in self.size_categories.keys():
            count = sum(1 for b in self.bubbles 
                       if self.size_categories[category][0] <= b.size <= self.size_categories[category][1])
            if count < self.max_per_size:
                if random.random() < 0.1:  # 10% chance per frame
                    self.spawn_bubble(category)
    
    def render(self) -> list[str]:
        """Render all bubbles to a canvas."""
        # Create canvas
        canvas = [[' ' for _ in range(self.terminal_width)] 
                 for _ in range(self.terminal_height)]
        
        # Render each bubble
        for bubble in self.bubbles:
            # Render bubble
            radius = int(bubble.current_size) + 1
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    x = int(bubble.x) + dx
                    y = int(bubble.y) + dy
                    
                    if 0 <= x < self.terminal_width and 0 <= y < self.terminal_height:
                        char = bubble.get_char(dx, dy)
                        if char != ' ':
                            canvas[y][x] = bubble.color + char + Colors.RESET
        
        # Convert to strings
        return [''.join(row) for row in canvas]


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
    refresh_interval: float = 0.1,  # Faster updates for smooth animation
    date_filter: str | None = None,
    expected_total: int | None = None,
):
    """Monitor process with floating bubble animation."""
    if features_dir is None:
        features_dir = Path("data/features")
    
    # Terminal dimensions
    terminal_width = 80
    terminal_height = 24
    
    # Bubble system
    bubble_system = BubbleSystem(terminal_width, terminal_height)
    
    # Initial counts
    initial_images = count_local_images(local_dir, date_filter)["total"]
    initial_feature_count = count_features(features_dir)
    
    start_time = time.time()
    last_update = start_time
    
    # Spawn initial bubbles
    for _ in range(5):
        category = random.choice(list(bubble_system.size_categories.keys()))
        bubble_system.spawn_bubble(category)
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            elapsed = current_time - start_time
            
            # Get current counts
            image_stats = count_local_images(local_dir, date_filter)
            current_images = image_stats["total"]
            current_features = count_features(features_dir)
            
            newly_downloaded = current_images - initial_images
            newly_extracted = current_features - initial_feature_count
            
            # Calculate progress percentage
            if expected_total and expected_total > 0:
                progress = min(100.0, (newly_downloaded / expected_total) * 100.0)
            else:
                # Estimate progress based on elapsed time (if we have a rough estimate)
                progress = min(100.0, (elapsed / 3600.0) * 100.0)  # Assume 1 hour max
            
            # Calculate rates
            if elapsed > 0:
                image_rate = newly_downloaded / elapsed
                feature_rate = newly_extracted / elapsed
            else:
                image_rate = 0
                feature_rate = 0
            
            # Update bubble system
            bubble_system.update(dt, progress)
            
            # Clear screen
            print(Colors.CLEAR, end='')
            
            # Header
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            print()
            
            # Stats (normal text)
            time_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
            print(Colors.CREAM + f"Time: {time_str}" + Colors.RESET)
            print()
            
            elapsed_min = int(elapsed // 60)
            elapsed_sec = int(elapsed % 60)
            print(Colors.MINT + f"Elapsed: {elapsed_min:02d}:{elapsed_sec:02d}" + Colors.RESET)
            print(Colors.PINK + f"Images: {newly_downloaded}" + Colors.RESET)
            if current_images > 0:
                print(Colors.CREAM + f"  (total: {current_images})" + Colors.RESET)
            print(Colors.MINT + f"Features: {newly_extracted}" + Colors.RESET)
            if current_features > 0:
                print(Colors.CREAM + f"  (total: {current_features})" + Colors.RESET)
            
            if image_rate > 0:
                print(Colors.CREAM + f"Rate: {image_rate:.2f} images/sec" + Colors.RESET)
            
            print(Colors.BLUE + f"Progress: {progress:.1f}%" + Colors.RESET)
            print()
            
            # Render bubbles
            bubble_canvas = bubble_system.render()
            for line in bubble_canvas:
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
                            print()
                            print(Colors.CREAM + "Latest log:" + Colors.RESET)
                            recent_lines = [l.strip() for l in lines[-10:] if l.strip()][-3:]
                            for line in recent_lines:
                                if len(line) > terminal_width - 4:
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bubble-themed process monitor with floating bubble animation",
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
        default=0.1,
        help="Refresh interval in seconds (default: 0.1 for smooth animation)",
    )
    parser.add_argument(
        "--date-filter",
        type=str,
        help="Date filter for images (YYYYMMDD format)",
    )
    parser.add_argument(
        "--expected-total",
        type=int,
        help="Expected total number of images for progress calculation",
    )
    
    args = parser.parse_args()
    
    monitor_process(
        local_dir=args.local_dir,
        features_dir=args.features_dir,
        log_file=args.log_file,
        refresh_interval=args.refresh_interval,
        date_filter=args.date_filter,
        expected_total=args.expected_total,
    )


if __name__ == "__main__":
    main()
