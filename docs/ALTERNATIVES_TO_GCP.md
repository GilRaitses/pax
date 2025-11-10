# Alternatives to Google Cloud Platform

## Current Issue
The Cloud Scheduler is triggering every 30 minutes but the Cloud Run job executions are failing (status code 2). This document outlines alternatives if Google services are not reliable or accessible.

## Alternative Solutions

### 1. AWS Lambda + EventBridge (Recommended)
**Pros:**
- Free tier: 1M requests/month, 400K GB-seconds compute
- Scheduled triggers via EventBridge (cron-like)
- Pay-per-use pricing
- Reliable and widely used

**Implementation:**
- Use AWS Lambda with Python runtime
- EventBridge rule: `rate(30 minutes)` or `cron(*/30 * * * ? *)`
- Store images in S3 (5 GB free tier)
- Cost: ~$0.20/month for 55K invocations

**Migration Steps:**
1. Create Lambda function with Docker container or zip deployment
2. Set up EventBridge rule for 30-minute schedule
3. Configure S3 bucket for image storage
4. Update collector script to use boto3 instead of google-cloud-storage

### 2. Azure Functions + Timer Trigger
**Pros:**
- Free tier: 1M requests/month
- Built-in timer triggers (cron format)
- Pay-per-execution pricing
- Good integration with Azure Storage

**Implementation:**
- Azure Function with TimerTrigger
- Cron expression: `0 */30 * * * *`
- Store images in Azure Blob Storage
- Cost: ~$0.20/month

**Migration Steps:**
1. Create Azure Function App
2. Deploy function with TimerTrigger
3. Configure Azure Blob Storage
4. Update collector to use azure-storage-blob

### 3. Self-Hosted: VPS + Cron + S3/MinIO
**Pros:**
- Full control
- No vendor lock-in
- Can use any storage backend
- Predictable costs

**Cons:**
- Requires maintaining server
- Need to handle uptime/reliability

**Implementation:**
- Rent VPS (DigitalOcean, Linode, etc.) - $5-10/month
- Set up cron job: `*/30 * * * *`
- Use S3-compatible storage (AWS S3, MinIO, Backblaze B2)
- Cost: ~$5-10/month + storage

**Migration Steps:**
1. Set up VPS with Docker
2. Install collector container
3. Configure cron job
4. Set up S3-compatible storage
5. Configure backup/monitoring

### 4. Railway / Render / Fly.io
**Pros:**
- Simple deployment
- Built-in cron support
- Managed infrastructure
- Free tiers available

**Implementation:**
- Deploy container to platform
- Use platform's cron/scheduler feature
- Store images in platform storage or S3
- Cost: Free tier or ~$5-20/month

### 5. GitHub Actions (Free Tier)
**Pros:**
- Free for public repos
- Built-in cron support
- No infrastructure to manage
- 2,000 minutes/month free

**Cons:**
- Limited to 2,000 minutes/month (would need ~1,440 minutes for 30-min schedule)
- Not ideal for frequent execution
- Better for daily/weekly tasks

**Implementation:**
- GitHub Actions workflow with `schedule: cron: '*/30 * * * *'`
- Store images in GitHub Releases or external storage
- Cost: Free (if within limits)

## Recommended Migration Path

### Option A: AWS Lambda (Best for Reliability)
1. **Setup:**
   ```bash
   # Create Lambda function
   aws lambda create-function \
     --function-name pax-collector \
     --runtime python3.11 \
     --handler collector.handler \
     --zip-file fileb://deployment.zip
   
   # Create EventBridge rule
   aws events put-rule \
     --name pax-collector-schedule \
     --schedule-expression "rate(30 minutes)"
   
   # Add Lambda permission
   aws lambda add-permission \
     --function-name pax-collector \
     --statement-id scheduler \
     --action lambda:InvokeFunction \
     --principal events.amazonaws.com
   ```

2. **Storage:** Use S3 bucket (same structure as GCS)

3. **Cost:** ~$0.20/month for 55K invocations

### Option B: Self-Hosted VPS (Best for Control)
1. **Setup:**
   ```bash
   # On VPS
   docker pull your-registry/pax-collector
   docker run -d --name pax-collector \
     -e PAX_REMOTE_PROVIDER=s3 \
     -e PAX_REMOTE_BUCKET=your-bucket \
     --restart unless-stopped \
     your-registry/pax-collector
   
   # Cron job
   */30 * * * * docker exec pax-collector python -m pax.scripts.collect_manifest
   ```

2. **Storage:** S3, MinIO, or Backblaze B2

3. **Cost:** $5-10/month VPS + storage

## Storage Alternatives

### AWS S3
- **Free tier:** 5 GB storage, 20K GET requests/month
- **Cost:** $0.023/GB/month after free tier
- **Compatible:** Yes, boto3 library

### Backblaze B2
- **Free tier:** 10 GB storage
- **Cost:** $0.005/GB/month (cheaper than S3)
- **Compatible:** Yes, boto3-compatible API

### MinIO (Self-Hosted)
- **Free:** Open source
- **Cost:** Just hosting costs
- **Compatible:** S3-compatible API

### Azure Blob Storage
- **Free tier:** 5 GB storage
- **Cost:** $0.0184/GB/month
- **Compatible:** azure-storage-blob library

## Migration Checklist

- [ ] Choose alternative platform
- [ ] Set up storage backend
- [ ] Update collector script for new storage provider
- [ ] Deploy collector to new platform
- [ ] Configure scheduler/cron
- [ ] Test collection cycle
- [ ] Migrate existing images (if needed)
- [ ] Update dashboard to use new storage
- [ ] Monitor for 24 hours
- [ ] Cancel Google Cloud resources

## Cost Comparison (2-week collection)

| Platform | Compute | Storage | Total |
|----------|---------|---------|-------|
| **GCP** | $0.00 (free tier) | $0.11 | $0.11 |
| **AWS Lambda** | $0.20 | $0.11 | $0.31 |
| **Azure Functions** | $0.20 | $0.10 | $0.30 |
| **VPS** | $5-10 | $0.11 | $5.11-10.11 |
| **Railway** | $5-20 | $0.11 | $5.11-20.11 |

## Next Steps

1. **First:** Diagnose why GCP scheduler is failing (check logs above)
2. **If GCP is blocked:** Choose AWS Lambda (most reliable) or VPS (most control)
3. **Migrate:** Follow migration checklist above
4. **Test:** Run for 24 hours before full migration

