# 🚀 Production Setup Guide - Sentry & Automated Backups

This guide covers the setup of **Sentry Error Monitoring** and **Automated Database Backups** for 100% production readiness.

---

## 📋 Table of Contents

1. [Sentry Error Monitoring Setup](#sentry-error-monitoring-setup)
2. [Automated Database Backups Setup](#automated-database-backups-setup)
3. [Environment Variables](#environment-variables)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

---

## 🔍 Sentry Error Monitoring Setup

### What is Sentry?

Sentry provides real-time error tracking, performance monitoring, and alerting. You'll receive instant notifications when errors occur in production.

### Step 1: Create Sentry Account

1. Go to **https://sentry.io/signup/**
2. Sign up for a free account (or paid plan for more features)
3. Create a new project
4. Select **Flask** as your platform
5. Copy your **DSN** (Data Source Name)

### Step 2: Configure Environment Variable

Add to your Render environment variables:

```
SENTRY_DSN=https://your-key@sentry.io/your-project-id
ENVIRONMENT=production
RELEASE_VERSION=1.0.0
```

**Optional:**
- `ENVIRONMENT`: Set to `production`, `staging`, or `development` (defaults to `production`)
- `RELEASE_VERSION`: Your app version (defaults to `1.0.0`)

### Step 3: Verify Integration

After deployment, Sentry will automatically:
- ✅ Capture all unhandled exceptions
- ✅ Track performance metrics
- ✅ Send real-time alerts to your email/Slack
- ✅ Provide detailed stack traces and context

### Step 4: Test Sentry Integration

Trigger a test error to verify:

```python
# In your app, add a test route (remove after testing):
@app.route('/test-sentry')
def test_sentry():
    raise Exception("Test error for Sentry")
```

Visit the route and check your Sentry dashboard - you should see the error appear within seconds.

---

## 💾 Automated Database Backups Setup

### What is Automated Backups?

Daily automated backups of your PostgreSQL database, stored securely in AWS S3 with automatic retention cleanup.

### Step 1: Create AWS S3 Bucket

1. Go to **https://aws.amazon.com/s3/**
2. Sign in to AWS Console
3. Create a new S3 bucket:
   - **Bucket name**: `employeesuite-backups` (or your preferred name)
   - **Region**: Choose closest to you (e.g., `us-east-1`)
   - **Block Public Access**: ✅ Enable (keep backups private)
   - **Versioning**: Optional (recommended for extra safety)

### Step 2: Create AWS IAM User for Backups

1. Go to **IAM** → **Users** → **Create User**
2. User name: `employeesuite-backup-user`
3. **Access type**: Programmatic access
4. **Permissions**: Attach policy `AmazonS3FullAccess` (or create custom policy for just your bucket)
5. **Save** the Access Key ID and Secret Access Key

### Step 3: Configure Environment Variables

Add to your Render environment variables:

```
# S3 Backup Configuration
S3_BACKUP_BUCKET=employeesuite-backups
S3_BACKUP_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
BACKUP_RETENTION_DAYS=30
```

**Configuration:**
- `S3_BACKUP_BUCKET`: Your S3 bucket name
- `S3_BACKUP_REGION`: AWS region where bucket is located
- `AWS_ACCESS_KEY_ID`: IAM user access key
- `AWS_SECRET_ACCESS_KEY`: IAM user secret key
- `BACKUP_RETENTION_DAYS`: How many days to keep backups (default: 30)

### Step 4: Set Up Automated Cron Job

#### Option A: Using Render Cron Jobs (Recommended)

1. In Render Dashboard → **Cron Jobs** → **New Cron Job**
2. **Name**: `Daily Database Backup`
3. **Schedule**: `0 2 * * *` (runs daily at 2 AM UTC)
4. **Command**: 
   ```bash
   curl -X POST "https://your-app.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET"
   ```
5. Replace `YOUR_CRON_SECRET` with your actual `CRON_SECRET` value

#### Option B: Using External Cron Service (e.g., cron-job.org)

1. Go to **https://cron-job.org** (or similar service)
2. Create new cron job:
   - **URL**: `https://your-app.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET`
   - **Schedule**: Daily at 2 AM
   - **Method**: POST

### Step 5: Verify Backup System

1. **Manual Test**: Visit the backup endpoint directly:
   ```
   https://your-app.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET
   ```
   Should return: `{"success": true, "backup_file": "employeesuite_backup_..."}`

2. **Check S3**: Go to your S3 bucket → `backups/` folder
   - You should see backup files like: `employeesuite_backup_20250105_020000.sql.gz`

3. **Check Logs**: Render logs should show:
   ```
   INFO: Creating database backup: employeesuite_backup_...
   INFO: Backup created successfully
   INFO: Uploading backup to S3
   INFO: Backup uploaded successfully to S3
   ```

---

## 🔧 Environment Variables Summary

### Required for Sentry:
```
SENTRY_DSN=https://your-key@sentry.io/your-project-id
```

### Required for Backups:
```
S3_BACKUP_BUCKET=your-bucket-name
S3_BACKUP_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Optional:
```
ENVIRONMENT=production
RELEASE_VERSION=1.0.0
BACKUP_RETENTION_DAYS=30
```

### Existing (Already Set):
```
CRON_SECRET=your-secret-key
DATABASE_URL=postgresql://...
```

---

## 🧪 Testing

### Test Sentry:

1. **Trigger Test Error:**
   ```bash
   curl https://your-app.onrender.com/test-sentry
   ```
   (Add test route temporarily, then remove)

2. **Check Sentry Dashboard:**
   - Should see error within 10 seconds
   - Check email for alert (if configured)

### Test Backups:

1. **Manual Backup:**
   ```bash
   curl -X POST "https://your-app.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET"
   ```

2. **Verify in S3:**
   - Check bucket for new backup file
   - Download and verify file size > 0

3. **Test Restore (Local):**
   ```bash
   python restore_backup.py --list
   python restore_backup.py --backup employeesuite_backup_20250105_020000.sql.gz
   ```

---

## 🔄 Restoring from Backup

### List Available Backups:

```bash
python restore_backup.py --list
```

### Restore a Backup:

```bash
python restore_backup.py --backup employeesuite_backup_20250105_020000.sql.gz
```

**⚠️ WARNING:** This will overwrite all existing data in your database!

**Prerequisites:**
- `pg_restore` must be installed locally
- Environment variables must be set (same as production)
- Database must be accessible

---

## 🐛 Troubleshooting

### Sentry Not Working:

1. **Check DSN:**
   - Verify `SENTRY_DSN` is set correctly
   - Check Sentry dashboard for project DSN

2. **Check Logs:**
   - Look for "Sentry error monitoring initialized" in logs
   - If you see "SENTRY_DSN not set", environment variable is missing

3. **Test Connection:**
   - Sentry dashboard should show "Issues" tab
   - Trigger test error to verify

### Backups Not Working:

1. **Check Environment Variables:**
   ```bash
   # In Render, verify all backup-related env vars are set
   ```

2. **Check AWS Credentials:**
   - Verify IAM user has S3 permissions
   - Check Access Key ID and Secret Key are correct

3. **Check S3 Bucket:**
   - Verify bucket name matches `S3_BACKUP_BUCKET`
   - Verify region matches `S3_BACKUP_REGION`
   - Check bucket permissions allow uploads

4. **Check pg_dump:**
   - Render should have `pg_dump` installed by default
   - If not, backups will fail with "command not found"

5. **Check Logs:**
   - Look for error messages in Render logs
   - Common errors:
     - "DATABASE_URL environment variable is required"
     - "S3 upload failed"
     - "pg_dump failed"

### Backup File Size is 0:

- Database might be empty
- Check database connection
- Verify `DATABASE_URL` is correct

### Cron Job Not Running:

1. **Check Cron Schedule:**
   - Verify cron expression is correct
   - Test with immediate execution first

2. **Check Secret:**
   - Verify `CRON_SECRET` matches in both places
   - Endpoint returns 401 if secret is wrong

3. **Check Endpoint:**
   - Test manually with curl
   - Check Render logs for errors

---

## 📊 Monitoring & Alerts

### Sentry Alerts:

1. **Email Alerts:**
   - Sentry → Settings → Alerts
   - Configure email notifications for errors

2. **Slack Integration:**
   - Sentry → Settings → Integrations
   - Add Slack webhook for real-time alerts

### Backup Monitoring:

1. **Check Backup Success:**
   - Monitor Render logs daily
   - Verify S3 bucket has recent backups

2. **Set Up S3 Alerts:**
   - AWS CloudWatch → Create alarm
   - Alert if no new backup in 25 hours

---

## ✅ Production Readiness Checklist

- [ ] Sentry account created and DSN configured
- [ ] `SENTRY_DSN` environment variable set in Render
- [ ] Test error sent to Sentry (verify it appears)
- [ ] AWS S3 bucket created for backups
- [ ] AWS IAM user created with S3 permissions
- [ ] All backup environment variables set in Render
- [ ] Manual backup test successful
- [ ] Backup file appears in S3 bucket
- [ ] Cron job configured (daily at 2 AM)
- [ ] Cron job test successful
- [ ] Backup retention working (old backups deleted)
- [ ] Restore script tested locally

---

## 🎯 Cost Estimates

### Sentry:
- **Free Tier**: 5,000 events/month (perfect for starting)
- **Team Plan**: $26/month (unlimited events, better features)

### AWS S3 Backups:
- **Storage**: ~$0.023/GB/month
- **Requests**: ~$0.005 per 1,000 requests
- **Estimated**: $1-5/month for daily backups (depends on DB size)

**Total Additional Cost: ~$2-31/month** (depending on plan choices)

---

## 🚀 You're All Set!

Your application now has:
- ✅ **Real-time error monitoring** (Sentry)
- ✅ **Automated daily backups** (S3)
- ✅ **Automatic retention cleanup** (30 days)
- ✅ **Backup restoration capability**

**Your app is now 100% production-ready with "set and forget" monitoring and backups!**

---

**Last Updated:** January 2025  
**Version:** 1.0
