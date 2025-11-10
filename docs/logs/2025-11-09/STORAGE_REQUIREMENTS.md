# Storage Requirements for 2-Week Collection

## Summary

**Purple Zone Cameras:** 82 cameras  
**Collection Period:** 14 days (2 weeks)  
**Images per camera per day:** 48 (every 30 minutes)  
**Total images:** 55,104 images

## Storage Calculations

### Per Day
- Images per day: 82 cameras × 48 images = **3,936 images/day**
- Storage per day: ~0.38 GB/day (assuming ~100KB per image)

### Total (14 days)
- Total images: 82 × 48 × 14 = **55,104 images**
- Total storage: **~5.38 GB** (assuming ~100KB per image average)

### Per Camera
- Images per camera: 48 × 14 = **672 images per camera** ✅
- Storage per camera: ~67 MB per camera

## GCS Storage Costs (Estimated)

### Standard Storage (US-EAST1)
- First 5 GB: Free
- Next 5 GB: $0.020 per GB/month
- **Estimated cost for 5.38 GB:** ~$0.11/month

### Operations Costs
- Class A operations (uploads): 55,104 × $0.05 per 10,000 = **$0.28**
- Class B operations (reads): Minimal (mostly writes)

### Total Estimated Cost
- **Storage:** ~$0.11/month
- **Operations:** ~$0.28
- **Total:** ~$0.39 for 2 weeks of collection

## Billing Requirements

✅ **Billing Account:** Linked to project  
✅ **Storage Class:** Standard (US-EAST1)  
✅ **Quota:** Well within free tier limits

## Collection Schedule

- **Frequency:** Every 30 minutes (`*/30 * * * *`)
- **Images per day:** 48 per camera
- **Total executions:** 48 per day × 14 days = 672 executions
- **Duration:** Each execution ~1-2 minutes

## Verification Checklist

- [x] 82 cameras in purple zone confirmed
- [x] Scheduler set to run every 30 minutes
- [x] Storage requirements calculated (~5.38 GB)
- [x] Billing account linked
- [x] GCS bucket exists and accessible
- [x] Cost estimate: ~$0.39 for 2 weeks

## Notes

- Storage is well within free tier (5 GB free)
- Operations costs are minimal
- No quota limits should be hit
- Collection will run automatically every 30 minutes for 2 weeks

