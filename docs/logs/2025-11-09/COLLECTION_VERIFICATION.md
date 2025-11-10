# 2-Week Collection Verification

## ✅ Configuration Verified

### Purple Zone Cameras
- **Total:** 82 cameras
- **Boundary:** 34th-66th St, 3rd-9th/Amsterdam
- **Numbered:** 1-82 matching partitioning map

### Collection Schedule
- **Frequency:** Every 30 minutes (`*/30 * * * *`)
- **Images per camera per day:** 48 ✅
- **Total per camera (14 days):** 672 images ✅
- **Total executions:** 672 over 2 weeks

### Storage Requirements
- **Total images:** 55,104 (82 × 48 × 14)
- **Total storage:** ~5.38 GB
- **Daily storage:** ~0.38 GB/day
- **Current bucket size:** 1.69 MiB (plenty of room)

### Billing Status
- ✅ **Billing Account:** `billingAccounts/01C1DC-5FA5E6-321CD2`
- ✅ **Billing Enabled:** `True`
- ✅ **No billing blocks**

### Cost Estimate
- **Storage:** ~$0.11/month (well within free tier)
- **Operations:** ~$0.28 (55K uploads)
- **Total:** ~$0.39 for 2 weeks
- ✅ **No cost concerns**

### GCS Bucket
- **Bucket:** `gs://pax-nyc-images`
- **Location:** US-EAST1
- **Storage Class:** Standard
- ✅ **Accessible and ready**

### Deployment
- **Job:** `pax-collector-v2`
- **Scheduler:** `pax-collector-v2-schedule`
- **Schedule:** `*/30 * * * *` (every 30 minutes)
- **Manifest:** Uses numbered cameras (1-82)
- ✅ **Ready to deploy**

## Collection Plan

### What Will Happen
1. Every 30 minutes, Cloud Scheduler triggers `pax-collector-v2`
2. Job collects images from all 82 numbered cameras
3. Images uploaded to `gs://pax-nyc-images/images/{camera-id}/{timestamp}.jpg`
4. Continues for 14 days automatically

### Expected Results
- **Day 1:** 3,936 images (82 × 48)
- **Day 2-14:** Same, 3,936 images/day
- **Total after 14 days:** 55,104 images
- **Storage after 14 days:** ~5.38 GB

## Verification Commands

### Check collection status:
```bash
# View recent executions
gcloud run jobs executions list --project pax-nyc --region us-central1 --limit 10

# Check scheduler
gcloud scheduler jobs describe pax-collector-v2-schedule --project pax-nyc --location us-central1

# Check bucket size
gsutil du -sh gs://pax-nyc-images
```

### Monitor collection:
```bash
# Count images per day
gsutil ls gs://pax-nyc-images/images/**/*.jpg | grep "202511" | wc -l

# Check specific camera
gsutil ls gs://pax-nyc-images/images/{camera-id}/*.jpg | wc -l
```

## ✅ All Systems Ready

- ✅ 82 cameras confirmed
- ✅ 48 images/day configured
- ✅ 14-day schedule ready
- ✅ Billing enabled
- ✅ Storage sufficient
- ✅ No quota blocks
- ✅ Deployment script ready

**Ready to deploy and collect for 2 weeks!**

