# Google Cloud Storage Setup for Vasudeva Documents

This guide walks you through setting up Google Cloud Storage (GCS) to host the Vasudeva wisdom documents for deployment on Vercel.

## Why GCS?

The PDF documents (72.3 MB total) are too large to commit to Git. GCS provides:
- **Free tier**: 5 GB storage + 100 GB egress/month (plenty for our needs)
- **Reliability**: 99.95% availability SLA
- **Simple integration**: Easy to download on app startup

## Step 1: Create Google Cloud Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Accept terms of service
4. **New users get $300 free credit for 90 days!**

## Step 2: Create a New Project

1. Click the project dropdown at the top
2. Click **"New Project"**
3. Name it: `vasudeva-rag` (or your preferred name)
4. Click **"Create"**
5. Wait for project creation (~30 seconds)
6. Note your **Project ID** (e.g., `vasudeva-rag-123456`)

## Step 3: Create a GCS Bucket

1. Go to **Cloud Storage** → **Buckets** (or search "Cloud Storage")
2. Click **"Create Bucket"**
3. Configure bucket:
   - **Name**: `vasudeva-documents` (must be globally unique, try adding numbers if taken)
   - **Location type**: Region
   - **Location**: Choose closest to your users (e.g., `us-central1` for US)
   - **Storage class**: Standard
   - **Access control**: Uniform
   - **Protection tools**: None (for now)
4. Click **"Create"**

## Step 4: Upload Documents

### Option A: Web Console (Easiest)

1. Open your bucket
2. Click **"Upload Files"**
3. Select all 5 PDFs from your local `documents/` folder:
   - `KRSNA_Book_Vol.2_1970_ISKCON_Press_edition_SCAN.pdf`
   - `SB3.1.pdf`
   - `Srimad_Bhagavatam_Kamala_Subramaniam.pdf`
   - `source2.pdf`
   - `ttd.pdf`
4. Wait for upload to complete

### Option B: Using gcloud CLI (Advanced)

```bash
# Install gcloud CLI first: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Upload all PDFs
gsutil -m cp documents/*.pdf gs://vasudeva-documents/
```

## Step 5: Make Bucket Public (Recommended)

Since these are public religious texts, we'll make the bucket publicly readable.

1. Go to your bucket → **Permissions** tab
2. Click **"Grant Access"**
3. Add principal: `allUsers`
4. Role: **Storage Object Viewer**
5. Click **"Save"**
6. Confirm by clicking **"Allow Public Access"**

✅ Your documents are now publicly accessible!

### Test Public Access

Visit: `https://storage.googleapis.com/YOUR_BUCKET_NAME/SB3.1.pdf`

If it downloads, you're all set!

## Step 6: Get Configuration Values

You'll need these for your environment variables:

- **GCS_BUCKET_NAME**: Your bucket name (e.g., `vasudeva-documents`)
- **GCS_PROJECT_ID**: Your project ID (e.g., `vasudeva-rag-123456`)

## Step 7: Configure Environment Variables

### Local Development

Create/update `.env` file:
```bash
# OpenAI
OPENAI_API_KEY=your_openai_key_here

# GCS Configuration
GCS_BUCKET_NAME=vasudeva-documents
GCS_PROJECT_ID=vasudeva-rag-123456
```

### Vercel Deployment

1. Go to your Vercel project settings
2. Navigate to **Environment Variables**
3. Add:
   - `GCS_BUCKET_NAME` = `vasudeva-documents`
   - `GCS_PROJECT_ID` = `vasudeva-rag-123456`
   - `OPENAI_API_KEY` = `your_openai_key`

## Alternative: Private Bucket (Optional)

If you prefer to keep documents private:

### 1. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create vasudeva-reader \
    --display-name="Vasudeva Document Reader"

# Grant storage viewer access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:vasudeva-reader@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# Create key
gcloud iam service-accounts keys create key.json \
    --iam-account=vasudeva-reader@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 2. Add to Environment Variables

```bash
# Convert key.json to single-line JSON
GCS_CREDENTIALS_JSON=$(cat key.json | tr -d '\n')
```

Add to `.env`:
```bash
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

## Troubleshooting

### Documents not downloading
- Check bucket name is correct
- Verify bucket is public or credentials are valid
- Check internet connectivity

### "403 Forbidden" errors
- Bucket is not public AND no credentials provided
- Make bucket public or add service account credentials

### Large download times
- Consider using CDN (Cloudflare R2 has free egress)
- Check your bucket region (should be close to Vercel deployment region)

## Cost Monitoring

GCS is free for your usage, but to monitor:

1. Go to **Billing** → **Reports**
2. Filter by service: Cloud Storage
3. You should see near-zero costs

**Expected monthly usage:**
- Storage: 0.07 GB (~$0.002/month)
- Egress: ~1-5 GB depending on deployments (free tier)

## Next Steps

After setup:
1. ✅ Test code changes locally
2. ✅ Deploy to Vercel with environment variables
3. ✅ Verify first cold start downloads documents
4. ✅ Test guidance requests

---

**Questions?** Check the [implementation plan](file:///Users/ram/.gemini/antigravity/brain/49ec868d-45b4-457f-8b0b-b84100c19741/implementation_plan.md) for code integration details.
