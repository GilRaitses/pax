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
class Speck:
    """A small speck for the progress curtain."""
    x: float
    y: float
    vx: float  # Horizontal velocity
    vy: float  # Vertical velocity
    size: float  # Size (very small)
    color: str  # Speck color
    char: str  # Character to display
    lifetime: float  # How long speck has existed
    
    def update(self, dt: float, terminal_width: int, terminal_height: int, wind_x: float, wind_y: float):
        """Update speck physics with wind."""
        # Apply wind forces
        wind_strength = 1.2  # Specks are lighter than bubbles
        self.vx += wind_x * wind_strength * dt
        self.vy += wind_y * wind_strength * dt
        
        # Air resistance
        damping = 0.92
        self.vx *= damping
        self.vy *= damping
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Wrap around edges
        if self.x < 0:
            self.x = terminal_width
        elif self.x > terminal_width:
            self.x = 0
        
        if self.y < 0:
            self.y = terminal_height
        elif self.y > terminal_height:
            self.y = 0
        
        # Update lifetime
        self.lifetime += dt


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
    
    def update(self, dt: float, terminal_width: int, terminal_height: int, wind_x: float = 0.0, wind_y: float = 0.0):
        """Update bubble physics with wind effects."""
        # Update orbit
        if self.orbit_radius > 0:
            self.orbit_angle += self.orbit_speed * dt
            self.x = self.orbit_center_x + math.cos(self.orbit_angle) * self.orbit_radius
            self.y = self.orbit_center_y + math.sin(self.orbit_angle) * self.orbit_radius
        
        # Apply wind forces (bubbles are light, so wind affects them more)
        wind_strength = 0.8  # How much wind affects bubbles
        self.vx += wind_x * wind_strength * dt
        self.vy += wind_y * wind_strength * dt
        
        # Air resistance (damping)
        damping = 0.95
        self.vx *= damping
        self.vy *= damping
        
        # Update position with velocity
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Bounce off edges (with some energy loss)
        if self.x < self.current_size:
            self.x = self.current_size
            self.vx = abs(self.vx) * 0.7
        elif self.x > terminal_width - self.current_size:
            self.x = terminal_width - self.current_size
            self.vx = -abs(self.vx) * 0.7
        
        if self.y < self.current_size:
            self.y = self.current_size
            self.vy = abs(self.vy) * 0.7
        elif self.y > terminal_height - self.current_size:
            self.y = terminal_height - self.current_size
            self.vy = -abs(self.vy) * 0.7
        
        # Update rotation (wind causes rotation)
        rotation_from_wind = (wind_x + wind_y) * 0.3
        self.rotation_speed += rotation_from_wind * dt * 0.1
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
        if dist > self.current_size + 0.5:
            return ' '
        
        # Create bubble shape
        edge_dist = abs(dist - self.current_size)
        
        # Use different characters for bubble effect
        if edge_dist < 0.3:
            return '○'  # Outer edge
        elif edge_dist < 0.6:
            return '◉'  # Near edge
        elif dist < self.current_size * 0.5:
            return '◯'  # Inner
        elif dist < self.current_size * 0.8:
            return '·'  # Middle glow
        else:
            return ' '


class SpeckSystem:
    """Manages progress curtain specks."""
    
    def __init__(self, terminal_width: int, terminal_height: int):
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height
        self.specks: list[Speck] = []
        self.wind_time = 0.0
        self.wind_gust_phase = random.uniform(0, 2 * math.pi)
        
        # Speck characters and colors (deep oceanic tones with sea foam wisps)
        self.speck_chars = ['·', '•', '▪', '▫', '▪', '·', '○', '◯']
        # Deep oceanic colors with occasional sea foam
        self.speck_colors = [
            '\033[38;5;17m',   # Deep ocean blue (very dark)
            '\033[38;5;18m',   # Dark navy blue
            '\033[38;5;19m',   # Deep sea blue
            '\033[38;5;20m',   # Ocean depth blue
            '\033[38;5;21m',   # Dark teal blue
            '\033[38;5;23m',   # Deep cyan-blue
            '\033[38;5;24m',   # Ocean teal
            '\033[38;5;25m',   # Deep aqua
            '\033[38;5;30m',   # Dark sea green
            '\033[38;5;31m',   # Deep teal
            '\033[2;38;5;23m', # Dim deep ocean
            '\033[2;38;5;24m', # Dim ocean teal
            # Sea foam wisps (lighter, occasional)
            '\033[38;5;51m',   # Bright sea foam cyan (rare)
            '\033[38;5;87m',   # Light sea foam (rare)
            '\033[97m',        # White sea foam (very rare)
        ]
        
        # Spawn initial specks - much denser for visible wind effect
        self.target_speck_count = terminal_width * terminal_height // 3  # Very dense curtain
        for _ in range(self.target_speck_count):
            self.spawn_speck()
    
    def spawn_speck(self, x: float | None = None, y: float | None = None):
        """Spawn a new speck with oceanic colors."""
        if x is None:
            x = random.uniform(0, self.terminal_width)
        if y is None:
            y = random.uniform(0, self.terminal_height)
        
        vx = random.uniform(-0.3, 0.3)
        vy = random.uniform(-0.2, 0.2)
        size = random.uniform(0.3, 0.6)
        
        char_idx = random.randint(0, len(self.speck_chars) - 1)
        
        # Weighted color selection: mostly deep ocean, occasional sea foam
        if random.random() < 0.05:  # 5% chance for sea foam (bright colors)
            # Sea foam colors (indices 12-14)
            color_idx = random.choice([12, 13, 14])
        else:
            # Deep oceanic tones (indices 0-11)
            color_idx = random.randint(0, 11)
        
        speck = Speck(
            x=x, y=y,
            vx=vx, vy=vy,
            size=size,
            color=self.speck_colors[color_idx],
            char=self.speck_chars[char_idx],
            lifetime=0.0,
        )
        self.specks.append(speck)
    
    def get_wind_at_position(self, x: float, y: float, t: float) -> tuple[float, float]:
        """Calculate wind vector (same as bubble system)."""
        base_angle = math.sin(t * 0.1) * 2 * math.pi
        base_strength = 0.5 + 0.3 * math.sin(t * 0.15)
        wind_x = math.cos(base_angle) * base_strength
        wind_y = math.sin(base_angle) * base_strength
        
        gust_x = math.sin(x * 0.1 + t * 0.3) * 0.4
        gust_y = math.cos(y * 0.1 + t * 0.25) * 0.4
        
        gust_phase = math.sin(t * 0.05 + self.wind_gust_phase)
        if abs(gust_phase) > 0.8:
            gust_strength = abs(gust_phase) * 1.5
            gust_x += math.cos(t * 0.2) * gust_strength
            gust_y += math.sin(t * 0.18) * gust_strength
        
        return wind_x + gust_x, wind_y + gust_y
    
    def update(self, dt: float, progress: float):
        """Update all specks."""
        self.wind_time += dt
        
        # Update specks
        for speck in self.specks:
            wind_x, wind_y = self.get_wind_at_position(
                speck.x, speck.y, self.wind_time
            )
            speck.update(dt, self.terminal_width, self.terminal_height, wind_x, wind_y)
        
        # Maintain speck count - keep it dense
        while len(self.specks) < self.target_speck_count:
            self.spawn_speck()
        
        # Occasionally spawn extra specks in progress area for visible wind
        progress_width = int((progress / 100.0) * self.terminal_width)
        if progress_width > 0 and random.random() < 0.3:  # 30% chance per frame
            # Spawn a few specks in the progress area
            for _ in range(3):
                x = random.uniform(0, progress_width)
                y = random.uniform(0, self.terminal_height)
                self.spawn_speck(x, y)
    
    def render(self, progress: float) -> tuple[list[str], list[str]]:
        """Render specks as background and progress curtain.
        
        Returns:
            Tuple of (background_canvas, progress_canvas)
            - background_canvas: All specks across full width (whirly background)
            - progress_canvas: Specks only within progress area (progress curtain)
        """
        # Background canvas (all specks)
        bg_canvas = [[' ' for _ in range(self.terminal_width)] 
                    for _ in range(self.terminal_height)]
        
        # Progress canvas (only progress area)
        progress_canvas = [[' ' for _ in range(self.terminal_width)] 
                          for _ in range(self.terminal_height)]
        
        # Calculate progress width
        progress_width = int((progress / 100.0) * self.terminal_width)
        
        # Render specks
        for speck in self.specks:
            x = int(speck.x)
            y = int(speck.y)
            
            if 0 <= x < self.terminal_width and 0 <= y < self.terminal_height:
                # Always render to background
                bg_canvas[y][x] = speck.color + speck.char + Colors.RESET
                
                # Also render to progress canvas if within progress area
                if x < progress_width:
                    progress_canvas[y][x] = speck.color + speck.char + Colors.RESET
        
        return [''.join(row) for row in bg_canvas], [''.join(row) for row in progress_canvas]


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
        
        # Wind system
        self.wind_base_x = 0.0
        self.wind_base_y = 0.0
        self.wind_time = 0.0
        self.wind_gust_phase = random.uniform(0, 2 * math.pi)
    
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
    
    def get_wind_at_position(self, x: float, y: float, t: float) -> tuple[float, float]:
        """Calculate wind vector at a given position (varies by space and time)."""
        # Base wind (slowly changing direction)
        base_angle = math.sin(t * 0.1) * 2 * math.pi
        base_strength = 0.5 + 0.3 * math.sin(t * 0.15)
        wind_x = math.cos(base_angle) * base_strength
        wind_y = math.sin(base_angle) * base_strength
        
        # Local gusts (varies by position)
        gust_x = math.sin(x * 0.1 + t * 0.3) * 0.4
        gust_y = math.cos(y * 0.1 + t * 0.25) * 0.4
        
        # Occasional strong gusts
        gust_phase = math.sin(t * 0.05 + self.wind_gust_phase)
        if abs(gust_phase) > 0.8:  # Strong gust
            gust_strength = abs(gust_phase) * 1.5
            gust_x += math.cos(t * 0.2) * gust_strength
            gust_y += math.sin(t * 0.18) * gust_strength
        
        return wind_x + gust_x, wind_y + gust_y
    
    def update(self, dt: float, progress: float):
        """Update all bubbles and handle progress changes."""
        # Update wind time
        self.wind_time += dt
        
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
        
        # Update all bubbles with wind
        for bubble in self.bubbles:
            # Get wind at bubble's position
            wind_x, wind_y = self.get_wind_at_position(
                bubble.x, bubble.y, self.wind_time
            )
            bubble.update(dt, self.terminal_width, self.terminal_height, wind_x, wind_y)
        
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


def count_features(features_dir: Path) -> tuple[int, set[str], dict | None]:
    """Count extracted features and return set of analyzed image paths and last feature vector.
    
    Returns:
        Tuple of (total_features_count, set_of_analyzed_image_paths, last_feature_vector)
    """
    if not features_dir.exists():
        return 0, set(), None
    
    count = 0
    analyzed_images = set()
    last_feature = None
    
    # Get all feature files sorted by modification time
    feature_files = sorted(features_dir.glob("features_*.json"), key=lambda p: p.stat().st_mtime)
    
    for json_file in feature_files:
        try:
            import json
            with open(json_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    # List of feature vectors
                    count += len(data)
                    for item in data:
                        if isinstance(item, dict) and "image_path" in item:
                            analyzed_images.add(item["image_path"])
                            last_feature = item  # Keep last one
                elif isinstance(data, dict):
                    # Dictionary with features list
                    features_list = data.get("features", [])
                    count += len(features_list)
                    for item in features_list:
                        if isinstance(item, dict) and "image_path" in item:
                            analyzed_images.add(item["image_path"])
                            last_feature = item  # Keep last one
        except Exception:
            continue
    
    return count, analyzed_images, last_feature


def parse_progress_from_log(log_file: Path) -> dict:
    """Parse progress information from log file.
    
    Returns:
        Dict with 'current', 'total', 'percent', 'elapsed', 'remaining', 'rate'
    """
    if not log_file or not log_file.exists():
        return {}
    
    try:
        with open(log_file) as f:
            lines = f.readlines()
        
        # Look for progress bar lines (e.g., "Extracting features: 49%|████▉     | 1996/4051 [1:39:10<2:23:38,  4.19s/it]")
        progress_info = {}
        for line in reversed(lines[-100:]):  # Check last 100 lines
            line = line.strip()
            
            # Match progress bar pattern (handles Unicode block characters)
            import re
            # Pattern: "Extracting features: XX%| [blocks] | NNNN/TTTT [HH:MM:SS<HH:MM:SS, R.R"
            # The block characters can be any Unicode blocks, so we match anything between %| and |
            match = re.search(r'(\d+)%[|][^|]*[|]\s*(\d+)/(\d+)\s*\[([\d:]+)<([\d:]+),\s*([\d.]+)', line)
            if match:
                progress_info = {
                    'percent': float(match.group(1)),
                    'current': int(match.group(2)),
                    'total': int(match.group(3)),
                    'elapsed': match.group(4),
                    'remaining': match.group(5),
                    'rate': float(match.group(6)),
                }
                break
        
        return progress_info
    except Exception:
        return {}


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
    
    # Speck system for progress curtain
    speck_system = SpeckSystem(terminal_width, terminal_height)
    
    # Initial counts
    initial_images = count_local_images(local_dir, date_filter)["total"]
    initial_feature_count, initial_analyzed_images, _ = count_features(features_dir)
    
    start_time = time.time()
    last_update = start_time
    
    # Spawn initial bubbles
    for _ in range(5):
        category = random.choice(list(bubble_system.size_categories.keys()))
        bubble_system.spawn_bubble(category)
    
    # Make sure we have bubbles
    if len(bubble_system.bubbles) == 0:
        # Force spawn at least one of each size
        for category in bubble_system.size_categories.keys():
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
            current_features, analyzed_images, last_feature = count_features(features_dir)
            
            # Parse progress from log file (more accurate)
            log_progress = parse_progress_from_log(log_file)
            
            # Use log progress if available, otherwise calculate from counts
            if log_progress:
                images_analyzed = log_progress.get('current', len(analyzed_images))
                progress = log_progress.get('percent', 0.0)
            else:
                # Images analyzed = images that have features extracted
                images_analyzed = len(analyzed_images)
                
                # Calculate progress percentage (based on images analyzed)
                if expected_total and expected_total > 0:
                    progress = min(100.0, (images_analyzed / expected_total) * 100.0)
                elif current_images > 0:
                    # Progress based on how many images have been analyzed vs available
                    progress = min(100.0, (images_analyzed / current_images) * 100.0)
                else:
                    # Estimate progress based on elapsed time (if we have a rough estimate)
                    progress = min(100.0, (elapsed / 3600.0) * 100.0)  # Assume 1 hour max
            
            # Newly downloaded (for progress tracking)
            newly_downloaded = current_images - initial_images
            
            # Calculate rates (based on images analyzed)
            if elapsed > 0:
                image_rate = images_analyzed / elapsed
                feature_rate = current_features / elapsed
            else:
                image_rate = 0
                feature_rate = 0
            
            # Update bubble system
            bubble_system.update(dt, progress)
            
            # Update speck system
            speck_system.update(dt, progress)
            
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
            
            # Show progress from log if available
            if log_progress:
                print(Colors.PINK + f"Images Analyzed: {log_progress.get('current', images_analyzed)}/{log_progress.get('total', current_images)}" + Colors.RESET)
                if log_progress.get('rate'):
                    print(Colors.CREAM + f"  Rate: {log_progress['rate']:.1f} images/sec" + Colors.RESET)
                if log_progress.get('remaining'):
                    print(Colors.CREAM + f"  Remaining: {log_progress['remaining']}" + Colors.RESET)
            else:
                print(Colors.PINK + f"Images Analyzed: {images_analyzed}" + Colors.RESET)
                if current_images > 0:
                    print(Colors.CREAM + f"  (available: {current_images})" + Colors.RESET)
            
            print(Colors.BLUE + f"Progress: {progress:.1f}%" + Colors.RESET)
            print()
            
            # Render specks: background (full width) and progress curtain
            bg_speck_canvas, progress_speck_canvas = speck_system.render(progress)
            
            # Render bubbles on top
            bubble_canvas = bubble_system.render()
            
            # Combine: background specks + progress specks + bubbles
            # Create a combined canvas character by character
            combined_canvas = [[' ' for _ in range(terminal_width)] 
                              for _ in range(terminal_height)]
            
            def parse_ansi_line(line: str, canvas_row: list, start_x: int = 0):
                """Parse a line with ANSI codes and place characters in canvas row."""
                x_pos = start_x
                i = 0
                current_color = ''
                while i < len(line) and x_pos < terminal_width:
                    # Check for ANSI escape sequence
                    if line[i] == '\033':
                        # Capture ANSI code
                        ansi_start = i
                        while i < len(line) and line[i] != 'm':
                            i += 1
                        if i < len(line):
                            current_color = line[ansi_start:i+1]
                            i += 1
                        continue
                    
                    # Regular character
                    char = line[i]
                    if char != ' ' and x_pos < terminal_width:
                        canvas_row[x_pos] = current_color + char + Colors.RESET
                        x_pos += 1
                    i += 1
            
            # First, place background specks (full width, whirly background)
            for y in range(min(len(bg_speck_canvas), terminal_height)):
                parse_ansi_line(bg_speck_canvas[y], combined_canvas[y])
            
            # Then, overlay progress specks (only in progress area, brighter)
            for y in range(min(len(progress_speck_canvas), terminal_height)):
                line = progress_speck_canvas[y]
                x_pos = 0
                i = 0
                current_color = ''
                progress_width = int((progress / 100.0) * terminal_width)
                while i < len(line) and x_pos < progress_width:
                    # Check for ANSI escape sequence
                    if line[i] == '\033':
                        ansi_start = i
                        while i < len(line) and line[i] != 'm':
                            i += 1
                        if i < len(line):
                            current_color = line[ansi_start:i+1]
                            i += 1
                        continue
                    
                    char = line[i]
                    if char != ' ' and x_pos < terminal_width:
                        # Make progress specks brighter/more visible
                        combined_canvas[y][x_pos] = current_color + char + Colors.RESET
                        x_pos += 1
                    i += 1
            
            # Finally, overlay bubbles (they overwrite specks)
            # Parse bubble canvas more carefully to preserve positions
            for y in range(min(len(bubble_canvas), terminal_height)):
                line = bubble_canvas[y]
                x_pos = 0
                i = 0
                current_color = ''
                
                # Build a list of (position, char, color) tuples
                bubble_chars = []
                while i < len(line):
                    # Check for ANSI escape sequence
                    if line[i] == '\033':
                        ansi_start = i
                        while i < len(line) and line[i] != 'm':
                            i += 1
                        if i < len(line):
                            current_color = line[ansi_start:i+1]
                            i += 1
                        continue
                    
                    char = line[i]
                    if char != ' ':
                        bubble_chars.append((x_pos, char, current_color))
                    x_pos += 1
                    i += 1
                
                # Now place bubble characters, overwriting background
                for x_pos, char, color in bubble_chars:
                    if 0 <= x_pos < terminal_width:
                        combined_canvas[y][x_pos] = color + char + Colors.RESET
            
            # Print combined canvas
            for y in range(terminal_height):
                line = ''.join(combined_canvas[y])
                print(line)
            
            # Feature summary section below bubbles
            print()
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            
            # Try to load and display feature matrix from last processed image
            feature_summary_shown = False
            if last_feature and isinstance(last_feature, dict):
                print(Colors.CREAM + "Feature Matrix (Last Image):" + Colors.RESET)
                
                # Extract spatial features
                spatial = last_feature.get('spatial', {}) or last_feature.get('yolo', {}) or {}
                if spatial:
                    ped = spatial.get('pedestrian_count', 0)
                    veh = spatial.get('vehicle_count', 0)
                    bike = spatial.get('bicycle_count', 0)
                    total = spatial.get('total_object_count', ped + veh + bike)
                    crowd_density = spatial.get('crowd_density', 0.0)
                    
                    print(Colors.MINT + f"  Objects: Ped={ped} | Veh={veh} | Bike={bike} | Total={total}" + Colors.RESET)
                    if crowd_density > 0:
                        print(Colors.MINT + f"  Density: {crowd_density:.2f}" + Colors.RESET)
                    feature_summary_shown = True
                
                # Extract visual complexity if available
                visual = last_feature.get('visual_complexity', {}) or last_feature.get('detectron2', {}) or {}
                if visual:
                    scene_complexity = visual.get('scene_complexity', 0.0)
                    lighting = visual.get('lighting_condition', 'unknown')
                    if scene_complexity > 0 or lighting != 'unknown':
                        print(Colors.MINT + f"  Scene: Complexity={scene_complexity:.2f} | Lighting={lighting}" + Colors.RESET)
                        feature_summary_shown = True
                
                # Extract CLIP semantic scores if available
                semantic = last_feature.get('semantic_scores', {}) or last_feature.get('clip', {}) or {}
                if semantic and isinstance(semantic, dict):
                    top_scene = semantic.get('top_scene', '') or max(semantic.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)[0] if semantic else ''
                    if top_scene:
                        print(Colors.MINT + f"  Scene Label: {top_scene}" + Colors.RESET)
                        feature_summary_shown = True
            
            # Show feature file location if available
            if features_dir.exists():
                feature_files = list(features_dir.glob("features_*.json"))
                if feature_files:
                    latest_file = max(feature_files, key=lambda p: p.stat().st_mtime)
                    if not feature_summary_shown:
                        print(Colors.CREAM + "Features:" + Colors.RESET)
                    print(Colors.CREAM + f"  File: {latest_file.name}" + Colors.RESET)
                    print(Colors.CREAM + f"  Location: {features_dir}" + Colors.RESET)
            
            # Footer
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            print(Colors.CREAM + "Press Ctrl+C to stop" + Colors.RESET)
            print(Colors.BOLD + Colors.BLUE + "=" * terminal_width + Colors.RESET)
            
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
