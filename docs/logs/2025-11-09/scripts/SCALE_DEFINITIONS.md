# Scale Definitions for Partition Maps

## Overview

This document defines the different scales used in the partition map visualizations for the undirected graph search problem. Each scale serves a specific purpose in the multi-scale resolution analysis needed for Pareto front determination.

## Scale 1: Camera Zone Scale (Purple Zone)

**Boundary:** 34th-66th St, 3rd-9th/Amsterdam (above 59th St)

**Purpose:** Extended corridor for Pareto front analysis

**Characteristics:**
- Wider coverage area
- Includes all cameras needed for multi-scale resolution
- Encompasses the problem space (red zone)
- Used for determining Pareto-optimal solutions

**Cameras:** 82 cameras within corridor bounds

**Script:** `camera_corridor_partition.py`

**Output:** `camera_corridor_partition.png`

## Scale 2: Intersection Scale (Red Zone)

**Boundary:** 40th-61st St, Lex-8th/CPW (CPW above 60th St)

**Purpose:** Constrained problem space for graph search

**Characteristics:**
- Focused search space
- Defined by START (Grand Central) and GOAL (Carnegie Hall)
- Nested within camera corridor
- Used for actual pathfinding

**Intersections:** 161 intersection nodes

**Script:** `problem_space_partition.py` (master script)

**Output:** `problem_space.png`

## Scale Relationships

```
Camera Zone Scale (Purple)
    └── Intersection Scale (Red)
            └── START → GOAL path
```

The camera zone scale provides the extended context needed for Pareto front analysis, while the intersection scale defines the actual problem space for the graph search algorithm.

## Usage Guidelines

### When to Use Camera Zone Scale:
- Analyzing Pareto front conditions
- Understanding multi-scale resolution requirements
- Showing extended camera coverage
- Demonstrating relationship between problem space and coverage area

### When to Use Intersection Scale:
- Visualizing the actual search problem
- Showing START/GOAL relationship
- Focusing on the constrained problem space
- Creating publication-ready figures

## Future Scales

### Potential Scale 3: Intersection Detail Scale
- Focus on individual intersections
- Show detailed neighborhood structure
- Useful for local path optimization

### Potential Scale 4: Full Network Scale
- Entire Manhattan or NYC coverage
- Show complete camera network
- Context for city-wide analysis

