# OIDC vs OAuth for Cloud Scheduler: Why Jobs Need OAuth

## The Problem

Cloud Scheduler was configured to use **OIDC tokens** to authenticate with Cloud Run Jobs, but this was failing with 401 Unauthorized errors. After extensive troubleshooting of IAM permissions, the real issue was discovered: **Cloud Run Jobs require OAuth tokens, not OIDC tokens**.

## Why OIDC Was Tried First

### Initial Assumption (Incorrect)

1. **Similar Product Names:** Both "Cloud Run Services" and "Cloud Run Jobs" are Cloud Run products, leading to the assumption they work identically.

2. **Documentation Bias:** Most Cloud Scheduler examples and tutorials show Cloud Run Services, not Jobs. The OIDC authentication method is prominently featured for Services.

3. **Configuration Looked Correct:** The OIDC configuration was technically correct:
   - Service account: Correct ✅
   - Audience: Matched URI exactly ✅
   - IAM permissions: Granted correctly ✅
   - URI format: Correct ✅

4. **Error Was Misleading:** The 401 Unauthorized error suggested IAM/permission issues, not an authentication method mismatch.

5. **Standard Practice:** OIDC is the standard authentication method for Cloud Run Services, so it seemed logical to use it for Jobs too.

### Why It Took So Long

**Time Spent on Wrong Approach:**
- ~45 minutes troubleshooting IAM permissions
- Multiple attempts to fix OIDC configuration
- Checking service account permissions
- Verifying OIDC audience and service account
- Waiting for IAM propagation

**What Should Have Been Done:**
- Immediately checked if OIDC works with Cloud Run Jobs (it doesn't)
- Looked up Jobs-specific authentication requirements
- Tried OAuth tokens from the start

**The User's Key Insight:**
The user correctly identified that we had no Cloud Run Services set up, which led to questioning whether OIDC works with Jobs at all. This was the breakthrough that led to discovering OAuth tokens are required.

## Technical Differences

### OIDC (OpenID Connect) Tokens

**Purpose:** Identity verification and authentication

**How It Works:**
1. Cloud Scheduler generates an OIDC token using the service account
2. Token contains identity claims (who you are)
3. Cloud Run Service validates the token
4. Service verifies the caller's identity

**Works With:**
- ✅ Cloud Run **Services** (HTTP endpoints)
- ❌ Cloud Run **Jobs** (API invocations)

**Configuration:**
```bash
gcloud scheduler jobs create http JOB_NAME \
  --oidc-service-account-email=SERVICE_ACCOUNT \
  --oidc-token-audience=URL
```

**Use Case:** 
- Web services with HTTP endpoints
- APIs that need to verify caller identity
- Services that expose URLs

**Why It Works for Services:**
- Services have HTTP endpoints
- OIDC validates "who is calling this endpoint"
- Token is validated against the service's identity requirements

### OAuth Tokens

**Purpose:** Authorization and API access

**How It Works:**
1. Cloud Scheduler generates an OAuth access token
2. Token contains authorization scopes (what you can do)
3. Cloud Run Jobs API accepts the token
4. API authorizes the requested action

**Works With:**
- ✅ Cloud Run **Jobs** (API invocations)
- ✅ Cloud Run **Services** (also supported)

**Configuration:**
```bash
gcloud scheduler jobs create http JOB_NAME \
  --oauth-service-account-email=SERVICE_ACCOUNT \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
```

**Use Case:**
- Batch jobs invoked via API
- Scheduled tasks
- API calls that need authorization

**Why Jobs Need OAuth:**
- Jobs don't have HTTP endpoints - they're invoked via REST API
- The Cloud Run Jobs API expects OAuth access tokens
- OAuth authorizes "what action can be performed" (run job)
- OIDC only verifies "who you are" (not sufficient for API calls)

## Architectural Difference

### Cloud Run Services
```
Scheduler → HTTP Request → Service Endpoint
                        ↓
                   OIDC Token Validation
                        ↓
                   Process Request
```

**Flow:** HTTP request with OIDC token → Service validates identity → Process

### Cloud Run Jobs
```
Scheduler → HTTP Request → Jobs API Endpoint
                        ↓
                   OAuth Token Authorization
                        ↓
                   Create Job Execution
```

**Flow:** HTTP request with OAuth token → API authorizes action → Create execution

## Key Insight

**The fundamental difference:**
- **Services:** Have HTTP endpoints → Need identity verification (OIDC)
- **Jobs:** Invoked via API → Need action authorization (OAuth)

Even though both are "Cloud Run" products, they have different architectures and authentication requirements.

## The Fix

**Before (OIDC - Wrong for Jobs):**
```bash
gcloud scheduler jobs update http pax-collector-schedule \
  --oidc-service-account-email=COMPUTE_SA \
  --oidc-token-audience=JOB_URI
```

**After (OAuth - Correct for Jobs):**
```bash
gcloud scheduler jobs update http pax-collector-schedule \
  --oauth-service-account-email=COMPUTE_SA \
  --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"
```

**Result:**
- ✅ HTTP 200 (Success)
- ✅ Executions created successfully
- ✅ No authentication errors

## Lesson Learned

**Always verify authentication method matches resource type:**
- Cloud Run Services → OIDC tokens
- Cloud Run Jobs → OAuth tokens
- Don't assume similar products use the same authentication

**When troubleshooting:**
1. First verify the authentication method is correct for the resource type
2. Then check IAM permissions
3. Then check configuration details

**Documentation to check:**
- Cloud Run Jobs API documentation (not Services docs)
- Cloud Scheduler Jobs-specific examples (not Services examples)
- Authentication requirements for the specific resource type

