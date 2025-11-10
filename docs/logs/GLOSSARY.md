# Project Glossary

## Technical Terms Explained

### A* Search
A pathfinding algorithm that finds the shortest path from start to goal. It uses a "heuristic" (estimate) to guide the search efficiently.

**In our project:** Finds paths from Grand Central to Carnegie Hall, using stress scores to avoid difficult areas.

### Baseline
A starting point for comparison. In our case, the average stress/complexity score for each camera zone before we apply learned improvements.

### Camera Zone
A region of the map covered by a single camera. We have 82 camera zones in the purple corridor. Each zone has a Voronoi polygon (like a cell) that defines its coverage area.

### Edge Cases
Extreme examples - in our case, the most stressful (busiest) and least stressful (quietest) camera zones. These provide the most useful data for learning.

### Empirical Data Structure
A standardized format for storing information extracted from camera images. Like a form that always has the same fields: pedestrian count, vehicle count, complexity score, etc.

### Feature Vector
A list of numbers that describe something. For a camera zone, the feature vector might be: `[10 pedestrians, 5 cars, 0.8 complexity, 0.3 lighting, ...]`

### Heuristic
An estimate or guess that helps guide search. Manhattan distance is a simple heuristic ("how many blocks away?"). Our learned heuristic uses camera data ("how stressful is this area?").

### Knowledge Base
A structured way to store information about the map - which intersections connect, which zones cover which areas, etc. Like a database for the pathfinding algorithm.

### Learned Heuristic
A heuristic function that's learned from data (using machine learning) rather than being manually designed. Our learned heuristic predicts stress from camera features.

### Minimax
Focusing on extremes (minimum and maximum). In our case, we collect detailed data from the most and least stressful zones because they're most informative.

### Multi-Scale Resolution
Using different levels of detail:
- **Coarse (camera zone level):** "This whole area is stressful"
- **Fine (intersection level):** "This specific intersection is stressful"

### Non-Dominated Solution
A solution where you can't find another solution that's better in ALL objectives. If Path A is shorter but Path B is less stressful, neither dominates the other.

### Pareto Front
The set of optimal compromise solutions when you have multiple conflicting goals. Shows the trade-off: "If you want lower stress, you must accept longer distance."

### Pseudocode
Step-by-step description of an algorithm in plain language, like a recipe. Not actual code, but describes what the code should do.

### Ridge Regression
A machine learning technique that learns to predict a number (like stress score) from multiple inputs (like pedestrian count, vehicle count). It's simple, interpretable, and prevents overfitting.

### Stress Score
A number representing how difficult/complex it is to navigate through an area. Higher = more stressful (busy, crowded, complex). Lower = calmer (quiet, simple).

### Temporal Resolution
How frequently we collect data. "High temporal resolution" means collecting data very frequently (every 2 seconds) to see how things change over time.

### Voronoi Tessellation
A way to divide a map into regions (cells) where each cell contains all points closest to a specific camera. Like drawing boundaries around each camera so every location belongs to the nearest camera's zone.

## Process Explanations

### Baseline Generation Process
1. Collect images from all 82 cameras over 2 weeks (every 30 minutes)
2. Analyze each image with vision models to extract features
3. Compute average stress score for each camera zone
4. Create baseline heatmap showing stress distribution

### Fine-Grained Collection Process
1. Calculate stress scores for all zones from baseline data
2. Identify top 5 highest stress zones and bottom 5 lowest stress zones
3. Every hour, collect 30 images (one every 2 seconds) from these 10 zones
4. Track which zones have been collected (max 3 times per 6-hour period)
5. Rotate to different zones after limit reached

### Ridge Regression Training Process
1. Collect training data: feature vectors (from images) and stress scores (computed or labeled)
2. Train model: find weights that best predict stress from features
3. Validate: test on data model hasn't seen
4. Use: apply learned weights to predict stress for new camera zones

### Pareto Front Computation Process
1. Find all possible paths from start to goal
2. Score each path on multiple objectives (distance, stress, complexity)
3. Identify non-dominated solutions (can't improve one objective without hurting another)
4. Plot Pareto front showing trade-off curve
5. Present user with optimal compromise options

