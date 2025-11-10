# Checking IAM Permissions in Google Cloud Console

## Step-by-Step Guide

### 1. Check Cloud Run Job IAM Permissions

**Path:** Cloud Run → Jobs → pax-collector → Permissions

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Cloud Run** → **Jobs**
3. Click on **pax-collector**
4. Click on the **PERMISSIONS** tab
5. Look for `roles/run.invoker` role
6. Verify that `1019191232687-compute@developer.gserviceaccount.com` is listed as a member

**What to look for:**
- ✅ `roles/run.invoker` should exist
- ✅ `1019191232687-compute@developer.gserviceaccount.com` should be in the members list
- ✅ If missing, click "GRANT ACCESS" to add it

### 2. Check Project-Level IAM Permissions

**Path:** IAM & Admin → IAM

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **IAM & Admin** → **IAM**
3. Search for: `1019191232687-compute@developer.gserviceaccount.com`
4. Click on the service account to expand its roles

**What to look for:**
- ✅ `roles/iam.serviceAccountTokenCreator` (allows OIDC token creation)
- ✅ `roles/iam.serviceAccountUser` (if granted)
- ✅ `roles/run.admin` (if granted)

**To add missing permissions:**
1. Click the **pencil icon** (Edit) next to the service account
2. Click **ADD ANOTHER ROLE**
3. Select the role (e.g., `Service Account Token Creator`)
4. Click **SAVE**

### 3. Check Cloud Scheduler Configuration

**Path:** Cloud Scheduler → pax-collector-schedule

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Cloud Scheduler**
3. Click on **pax-collector-schedule**
4. Check the **Configuration** section

**What to verify:**
- **Target type:** HTTP
- **URL:** `https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/pax-nyc/jobs/pax-collector:run`
- **Auth header:** OIDC token
- **Service account:** `1019191232687-compute@developer.gserviceaccount.com`
- **Audience:** Should match the URL exactly

**To update OIDC configuration:**
1. Click **EDIT**
2. Scroll to **Auth header** section
3. Select **Add OIDC token**
4. **Service account:** `1019191232687-compute@developer.gserviceaccount.com`
5. **Audience:** `https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/pax-nyc/jobs/pax-collector:run`
6. Click **SAVE**

### 4. Test Scheduler and Check Execution Status

**Path:** Cloud Scheduler → pax-collector-schedule → RUN NOW

1. Go to **Cloud Scheduler**
2. Click on **pax-collector-schedule**
3. Click **RUN NOW** button (top right)
4. Wait 30 seconds
5. Go to **Cloud Run** → **Jobs** → **pax-collector** → **EXECUTIONS** tab
6. Check if a new execution appears

**What to look for:**
- ✅ New execution should appear within 30 seconds
- ✅ Execution status should show "Succeeded" (green checkmark)
- ❌ If no execution appears, check the **LOGS** tab in Cloud Scheduler

### 5. Check Scheduler Execution Logs

**Path:** Cloud Scheduler → pax-collector-schedule → LOGS

1. Go to **Cloud Scheduler**
2. Click on **pax-collector-schedule**
3. Click on **LOGS** tab
4. Look at the most recent entries

**What to look for:**
- ✅ **Status:** Should show "SUCCESS" or "OK"
- ❌ **Status:** "UNAUTHENTICATED" means OIDC is still failing
- **Debug info:** Will show HTTP response codes (401 = unauthorized)

### 6. Check Cloud Run Job Execution Logs

**Path:** Cloud Run → Jobs → pax-collector → EXECUTIONS → [execution name] → LOGS

1. Go to **Cloud Run** → **Jobs** → **pax-collector**
2. Click on **EXECUTIONS** tab
3. Click on the most recent execution
4. Click on **LOGS** tab

**What to look for:**
- ✅ Successful collection logs
- ❌ Error messages about authentication or permissions

## Quick Links

- **Cloud Run Jobs:** https://console.cloud.google.com/run/jobs?project=pax-nyc
- **Cloud Scheduler:** https://console.cloud.google.com/cloudscheduler?project=pax-nyc
- **IAM & Admin:** https://console.cloud.google.com/iam-admin/iam?project=pax-nyc

## Visual Indicators

### ✅ Good Signs:
- Green checkmarks next to executions
- "SUCCESS" status in scheduler logs
- New executions appearing after scheduler runs
- No 401 errors in logs

### ❌ Bad Signs:
- Red X marks next to executions
- "UNAUTHENTICATED" status in scheduler logs
- 401 HTTP response codes
- No executions created after scheduler runs

## If Permissions Look Correct But Still Failing

1. **Wait 5-10 minutes** for IAM propagation
2. **Try manually triggering** scheduler (RUN NOW button)
3. **Check logs** for specific error messages
4. **Verify OIDC audience** matches URL exactly (no trailing slashes, exact case)
5. **Consider AWS migration** if still failing after 10+ minutes

