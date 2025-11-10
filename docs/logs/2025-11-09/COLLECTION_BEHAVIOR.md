# Collection Behavior Verification

## ✅ Confirmed: 1 Image Every 30 Minutes Per Camera

### How It Works

**Each Execution (every 30 minutes):**
1. Cloud Scheduler triggers `pax-collector-v2` job
2. Job loads numbered manifest (82 cameras)
3. `collector.collect(camera_ids=[...82 cameras...])` is called
4. `fetch_snapshots(camera_ids)` fetches **1 image from each camera**
5. All 82 images are stored/uploaded

**Result per execution:**
- 82 images total (1 per camera)
- All captured at the same time (~30 seconds apart)

### Timeline

**Every 30 minutes:**
- Execution runs
- Collects 1 image from camera #1
- Collects 1 image from camera #2
- ... (continues for all 82 cameras)
- Total: 82 images stored

**Per day (48 executions):**
- Camera #1: 48 images ✅
- Camera #2: 48 images ✅
- ... (all 82 cameras)
- Camera #82: 48 images ✅
- **Total: 3,936 images/day**

**Over 14 days:**
- Each camera: 672 images ✅
- **Total: 55,104 images**

## Code Flow

```python
# collect_manifest.py
camera_ids = [cam["id"] for cam in cameras]  # All 82 cameras
collector.collect(camera_ids=camera_ids)      # Collect from all

# collector.py
raw_snapshots = self.client.fetch_snapshots(camera_ids)  # 1 per camera
for snapshot in snapshots:  # Loop through all 82
    storage_records.append(self._store_snapshot(snapshot))  # Store each
```

## ✅ Verification

- ✅ Scheduler: `*/30 * * * *` (every 30 minutes)
- ✅ Each execution: Collects from all 82 cameras
- ✅ Each camera: Gets 1 image per execution
- ✅ Per day: 48 images per camera
- ✅ Over 14 days: 672 images per camera

**This is exactly what you requested!**

