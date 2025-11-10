# Problem Space Visualization Requirements Checklist

## ✅ Completed Requirements

### 1. Street Labels (Y-axis)
- ✅ **Left side labels**: Match top avenue labels angle (-45 degrees), start from above (`va="top"`)
- ✅ **Right side labels**: Diagonal slant (-45 degrees), start from above (`va="top"`)
- ✅ **Added streets**: 45th, 49th, 55th (in addition to 42nd, 47th, 52nd, 57th)
- ✅ **49th Street special handling**: 
  - Left side: "W 49th St."
  - Right side: "E 49th St."
  - Code detects East vs West segments and positions labels accordingly

### 2. Avenue Labels (X-axis)
- ✅ **Bottom labels**: Diagonal slant (45 degrees), last letter touches axis line
- ✅ **Top labels**: Diagonal slant (-45 degrees), last letter touches axis line
- ✅ **8th Ave**: Separate label on bottom, does NOT include "Central Park West"
- ✅ **Central Park West**: Separate label on top/left side
- ✅ **Lexington**: Included in top labels (not in excluded list)
- ✅ **Central Park**: Single label replaces 6th/7th Ave on top axis

### 3. START/GOAL Markers and Lines
- ✅ **Dotted lines**: Extended past red boundary using `plot_xlim` + offset
- ✅ **Z-order**: Lines at zorder=15, text at zorder=16 (drawn on top)
- ✅ **Line visibility**: Increased linewidth to 2.5, alpha to 0.8
- ✅ **Line extension**: Lines connect from circles all the way to labels outside plot bounds

### 4. Plot Title
- ✅ **Title added**: "Manhattan Problem Space: Voronoi Tessellation with Traffic Camera Network"
- ✅ **Styling**: Fontsize 16, bold, color #2c3e50, pad=20

### 5. Other Features
- ✅ **Voronoi tessellation**: Deep purple lines (#4B0082), clipped to red boundary
- ✅ **Street grid**: Fainter grey for regular streets, deep yellow for major avenues
- ✅ **Central Park**: Green fill with label positioned inside park area
- ✅ **North arrow**: Positioned outside top-right corner

## Code Implementation Details

### Street Label Logic (lines 482-539)
- Left side: rotation=-45, va="top", ha="right"
- Right side: rotation=-45, va="top", ha="left"
- Special handling for 49th street with East/West detection

### START/GOAL Lines (lines 639-703)
- Uses `ax.get_xlim()` to get actual plot limits
- Extends lines with `label_offset_x = x_range * 0.12`
- High zorder (15 for lines, 16 for text) ensures visibility on top

### Top Avenue Labels (lines 899-956)
- Collects all labels except excluded ones (8th Ave, Broadway, 6th Ave, 7th Ave)
- Lexington is NOT excluded, so it should appear
- Uses `_top` positions if available, falls back to default positions

## Potential Issues to Verify

1. **Lexington on top**: Code logic looks correct, but if it's still missing, may need to check:
   - If Lexington has a `_top` position in `avenue_x_positions`
   - If Lexington's x position is within `red_x_min` to `red_x_max` bounds
   - If there's a data issue finding Lexington avenue segments

2. **Right side street labels**: Currently set to rotation=-45 (same as left). If user wants different angle, need clarification.

## Files Modified
- `src/pax/scripts/draw_problem_space.py`

