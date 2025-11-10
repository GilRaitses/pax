# Using Multi-Agent Work Tree with Cursor

## Overview

Cursor supports multi-agent workflows where you can run multiple AI agents in parallel on different tasks. This guide shows how to use the work tree structure with Cursor's multi-agent features.

## Quick Start

### Option 1: Using Cursor's Multi-Agent Chat

1. **Open Cursor** and navigate to the project
2. **Open a new chat** (Cmd/Ctrl + L)
3. **Reference the work tree:**
   ```
   I want to work on BRANCH 1: Vision Model Integration. 
   See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for task details.
   ```

4. **Start with a specific task:**
   ```
   Let's start Task 1.1: Set up YOLOv8n for object detection.
   Install ultralytics, create a wrapper script, and test on sample images.
   ```

### Option 2: Using Multiple Chat Windows

1. **Open multiple chat windows** (Cmd/Ctrl + L multiple times)
2. **Assign each chat to a different branch:**
   - Chat 1: "Working on BRANCH 1: Vision Model Integration"
   - Chat 2: "Working on BRANCH 2: Empirical Data Structure"
   - Chat 3: "Working on BRANCH 4: Visualization & Analysis"

3. **Each agent works independently** on their assigned branch

### Option 3: Using Cursor Composer (Multi-File Editing)

1. **Open Composer** (Cmd/Ctrl + I)
2. **Reference multiple tasks:**
   ```
   I want to work on BRANCH 1 and BRANCH 2 in parallel:
   - BRANCH 1: Set up YOLOv8n (Task 1.1)
   - BRANCH 2: Design feature vector schema (Task 2.2)
   
   See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for details.
   ```

## Example Prompts

### For BRANCH 1 (Vision Models)

```
I'm working on BRANCH 1: Vision Model Integration & Feature Extraction.

Current task: Task 1.1 - Set up YOLOv8n
- Install ultralytics package
- Create wrapper script in src/pax/vision/yolov8n.py
- Test on sample images from data/raw/images/
- Output: Pedestrian count, vehicle count, bike count

See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for full context.
```

### For BRANCH 2 (Data Structure)

```
I'm working on BRANCH 2: Empirical Data Structure Definition.

Current task: Task 2.2 - Design Feature Vector Schema
- Define spatial features (pedestrian count, vehicle count, density)
- Define visual complexity features
- Create Pydantic model in src/pax/schemas/feature_vector.py
- Document in docs/schemas/feature_vector_spec.md

See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for full context.
```

### For BRANCH 4 (Visualization)

```
I'm working on BRANCH 4: Visualization & Analysis.

Current task: Task 4.2 - Visualize Temporal Coverage
- Plot images by time of day
- Show coverage gaps
- Create script: scripts/2025-11-10/visualize_temporal_coverage.py
- Output: docs/figures/temporal_coverage.png

See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md for full context.
```

## Workflow Best Practices

### 1. Start with Independent Branches

Begin with branches that can run in parallel:
- ✅ BRANCH 1 (Vision Models)
- ✅ BRANCH 2 (Data Structure)
- ✅ BRANCH 4 (Visualization)

### 2. Coordinate Dependencies

When BRANCH 1 completes, notify agents working on:
- BRANCH 3 (Baseline Generation)
- BRANCH 5 (Infrastructure)

### 3. Use Clear Task References

Always reference the work tree file:
```
See agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md
Task X.Y: [Task Name]
```

### 4. Update Progress

As you complete tasks, update the work tree:
- Check off completed tasks: `- [x] Task X.Y`
- Update status in agent assignment files
- Document deliverables

## Example: Running Multiple Agents

### Session 1: Vision Models (Agent 1)
```
@agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md

I'm Agent 1 working on BRANCH 1.
Starting with Task 1.1: Set up YOLOv8n.

Create:
- src/pax/vision/__init__.py
- src/pax/vision/yolov8n.py (wrapper)
- tests/test_yolov8n.py (basic tests)
- requirements/vision.txt (dependencies)

Test on a few sample images from data/raw/images/
```

### Session 2: Data Structure (Agent 2)
```
@agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md

I'm Agent 2 working on BRANCH 2.
Starting with Task 2.2: Design Feature Vector Schema.

Create:
- src/pax/schemas/feature_vector.py (Pydantic model)
- docs/schemas/feature_vector_spec.md (documentation)
- examples/feature_vector_example.json (example)

The schema should include:
- Spatial features (pedestrian count, vehicle count, density)
- Visual complexity (scene complexity, lighting, weather)
- Temporal features (time encoding, day of week)
```

### Session 3: Visualization (Agent 3)
```
@agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md

I'm Agent 3 working on BRANCH 4.
Starting with Task 4.2: Visualize Temporal Coverage.

Create:
- scripts/2025-11-10/visualize_temporal_coverage.py
- Output: docs/figures/temporal_coverage.png

The script should:
- Load image metadata from GCS or local storage
- Plot images by time of day (hourly bins)
- Show coverage gaps
- Identify peak collection times
```

## Tracking Progress

### Update Work Tree

As tasks complete, update `MULTI_AGENT_WORK_TREE.md`:

```markdown
- [x] Task 1.1: Set up YOLOv8n ✅
- [ ] Task 1.2: Set up Detectron2
```

### Create Agent Assignment Files

Create files like `agentHandoff/worktrees/AGENT_1_BRANCH_1.md`:

```markdown
# Agent 1 - BRANCH 1 Assignment

**Status:** In Progress
**Started:** November 10, 2025

## Completed
- [x] Task 1.1: Set up YOLOv8n

## In Progress
- [ ] Task 1.2: Set up Detectron2

## Blocked
- None

## Notes
- YOLOv8n wrapper working, tested on 10 sample images
- Next: Set up Detectron2 for instance segmentation
```

## Tips

1. **Use @ mentions** to reference files:
   ```
   @agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md
   ```

2. **Be specific** about which task you're working on:
   ```
   Task 1.1: Set up YOLOv8n
   ```

3. **Reference dependencies** when needed:
   ```
   Waiting for BRANCH 1 to complete feature extraction before starting BRANCH 3
   ```

4. **Update the work tree** as you progress to keep everyone informed

5. **Use separate chat windows** for truly parallel work

## Troubleshooting

### "Agent doesn't know about the work tree"
- Explicitly reference the file: `@agentHandoff/worktrees/MULTI_AGENT_WORK_TREE.md`
- Copy the relevant task description into your prompt

### "Tasks are conflicting"
- Check dependencies in the work tree
- Ensure independent branches run in parallel
- Coordinate through the work tree file

### "Don't know where to start"
- Start with BRANCH 2 (Data Structure) - no dependencies
- Or BRANCH 4 (Visualization) - uses image metadata only
- Or BRANCH 1 (Vision Models) - foundational work

---

**Last Updated:** November 10, 2025  
**Cursor Version:** Latest (with multi-agent support)

