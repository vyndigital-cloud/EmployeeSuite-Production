# 🕐 CRON JOBS EXPLAINED - Complete Walkthrough

**What are cron jobs?** Automated tasks that run on a schedule (daily, hourly, etc.)

---

## 🎯 WHAT YOU HAVE (2 Cron Jobs)

### 1. **Trial Warning Emails** (`/cron/send-trial-warnings`)
**What it does:** Sends email warnings to users 1 day before their trial expires

**How it works:**
1. External service (cron-job.org) calls your endpoint daily
2. Your app checks all users whose trial expires tomorrow
3. Sends them a warning email: "Your trial expires in 1 day!"
4. Returns success/failure status

**Code flow:**
```
External Cron Service (cron-job.org)
    ↓ (calls daily at 9 AM UTC)
https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_SECRET
    ↓
app.py → cron_trial_warnings()
    ↓ (checks secret)
cron_jobs.py → send_trial_warnings()
    ↓ (finds users expiring tomorrow)
email_service.py → send_trial_expiry_warning()
    ↓
Email sent! ✅
```

**What it checks:**
- Users with `is_subscribed == False`
- Users whose `trial_ends_at` is between tomorrow and day after
- Sends email to each matching user

**Example:**
- Today: Jan 1
- User's trial expires: Jan 2
- Cron runs: Jan 1 at 9 AM
- Result: User gets email "Your trial expires in 1 day!"

---

### 2. **Database Backups** (`/cron/database-backup`)
**What it does:** Creates a backup of your database and uploads it to S3 (if configured)

**How it works:**
1. External service (cron-job.org) calls your endpoint daily
2. Your app creates a SQL dump of the database
3. Compresses it (gzip)
4. Uploads to AWS S3 (if configured)
5. Returns success/failure status

**Code flow:**
```
External Cron Service (cron-job.org)
    ↓ (calls daily at 2 AM UTC)
https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_SECRET
    ↓
app.py → cron_database_backup()
    ↓ (checks secret)
database_backup.py → run_backup()
    ↓ (creates SQL dump)
    ↓ (compresses with gzip)
    ↓ (uploads to S3 if configured)
Backup saved! ✅
```

**What it does:**
- Creates SQL dump: `employeesuite_backup_20250107_020000.sql`
- Compresses: `employeesuite_backup_20250107_020000.sql.gz`
- Uploads to S3: `s3://your-bucket/backups/employeesuite_backup_20250107_020000.sql.gz`
- Deletes old backups (if retention set)

**Example:**
- Cron runs: Jan 7 at 2 AM
- Creates: `employeesuite_backup_20250107_020000.sql.gz`
- Uploads to S3
- Result: Database backed up! ✅

---

## 🔐 SECURITY (How It Works)

**Both endpoints require a secret:**

```python
secret = request.args.get('secret')
if secret != os.getenv('CRON_SECRET'):
    return jsonify({"error": "Unauthorized"}), 401
```

**Why?** Prevents random people from triggering your cron jobs

**How to set it:**
1. Generate a random secret: `openssl rand -hex 32`
2. Add to Render: `CRON_SECRET=your-random-secret-here`
3. Use same secret in cron-job.org URLs

**Example URL:**
```
https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=abc123xyz789
```

---

## 🚀 SETUP GUIDE (Step-by-Step)

### Step 1: Get Your CRON_SECRET

**Option A: Generate locally**
```bash
openssl rand -hex 32
# Output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**Option B: Use online generator**
- Go to: https://randomkeygen.com/
- Copy a "CodeIgniter Encryption Keys" (64 characters)

**Then add to Render:**
1. Go to Render Dashboard → Your Service → Environment
2. Add: `CRON_SECRET` = `your-generated-secret`
3. Save

---

### Step 2: Set Up cron-job.org (FREE)

**1. Create Account:**
- Go to: https://cron-job.org
- Sign up (free)

**2. Create First Cron Job (Trial Warnings):**
- Click **"Create cronjob"**
- **Title:** `Trial Warning Emails`
- **Address:** 
  ```
  https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_CRON_SECRET
  ```
  (Replace `YOUR_CRON_SECRET` with your actual secret)
- **Schedule:** `Daily` at `09:00` UTC
- **Request Method:** `GET` (or `POST` - both work)
- Click **"Create cronjob"**

**3. Create Second Cron Job (Database Backup):**
- Click **"Create cronjob"** again
- **Title:** `Database Backup`
- **Address:**
  ```
  https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET
  ```
  (Same secret as above)
- **Schedule:** `Daily` at `02:00` UTC (2 AM - low traffic time)
- **Request Method:** `GET` (or `POST` - both work)
- Click **"Create cronjob"**

**Done!** ✅

---

## 🧪 TESTING (Verify It Works)

### Test Trial Warnings:

**Option 1: Manual Test (Browser)**
```
https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_CRON_SECRET
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Warnings sent"
}
```

**Option 2: Manual Test (Terminal)**
```bash
curl "https://employeesuite-production.onrender.com/cron/send-trial-warnings?secret=YOUR_CRON_SECRET"
```

**Check Render Logs:**
- Should see: `Sent X trial warning emails`

---

### Test Database Backup:

**Option 1: Manual Test (Browser)**
```
https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Backup completed successfully",
  "backup_file": "employeesuite_backup_20250107_020000.sql.gz",
  "s3_key": "backups/employeesuite_backup_20250107_020000.sql.gz",
  "timestamp": "2025-01-07T02:00:00Z"
}
```

**Option 2: Manual Test (Terminal)**
```bash
curl "https://employeesuite-production.onrender.com/cron/database-backup?secret=YOUR_CRON_SECRET"
```

**Check S3 (if configured):**
- Go to AWS S3 → Your bucket → `backups/` folder
- Should see backup file

**Check Render Logs:**
- Should see: `Automated backup completed: employeesuite_backup_...`

---

## ⚠️ TROUBLESHOOTING

### Problem: "Unauthorized" Error
**Cause:** Wrong secret or secret not set

**Fix:**
1. Check Render environment variables → `CRON_SECRET` is set
2. Check cron-job.org URL → secret matches exactly
3. Test manually with correct secret

---

### Problem: Trial Warnings Not Sending
**Cause:** No users expiring tomorrow, or email service issue

**Check:**
1. Render logs → Should see "Sent X trial warning emails"
2. If X = 0, no users are expiring tomorrow (this is normal!)
3. If error, check SendGrid API key

---

### Problem: Database Backup Failing
**Cause:** S3 not configured, or AWS credentials wrong

**Check:**
1. Render logs → Error message will tell you
2. If "S3 not configured" → This is OK, backup still created locally
3. If "AWS credentials invalid" → Check AWS env vars in Render

**Note:** Backups work WITHOUT S3! They just won't be uploaded.

---

## 📊 MONITORING

### cron-job.org Dashboard:
- Shows last execution time
- Shows success/failure status
- Shows response time
- Sends email alerts if job fails

### Render Logs:
- Check logs after cron runs
- Look for: `Sent X trial warning emails`
- Look for: `Automated backup completed`

### Sentry (if configured):
- Errors from cron jobs will appear in Sentry
- Set up alerts for cron failures

---

## 🎯 SCHEDULE RECOMMENDATIONS

### Trial Warnings:
- **Best time:** 9:00 AM UTC (morning in most timezones)
- **Frequency:** Daily
- **Why:** Users check email in the morning

### Database Backups:
- **Best time:** 2:00 AM UTC (lowest traffic)
- **Frequency:** Daily
- **Why:** Minimal impact on users, database is quiet

---

## 💡 PRO TIPS

1. **Test First:** Always test manually before relying on cron
2. **Monitor:** Check cron-job.org dashboard weekly
3. **Backup Secret:** Save your `CRON_SECRET` somewhere safe
4. **Multiple Secrets:** You can use different secrets for each job (optional)
5. **Alerts:** Set up email alerts in cron-job.org for failures

---

## ✅ QUICK CHECKLIST

- [ ] `CRON_SECRET` set in Render
- [ ] cron-job.org account created
- [ ] Trial warnings cron job created (9 AM UTC daily)
- [ ] Database backup cron job created (2 AM UTC daily)
- [ ] Both jobs tested manually
- [ ] Both jobs show "success" in cron-job.org
- [ ] Email alerts configured (optional)

---

## 🚀 YOU'RE DONE!

Once set up, these run **automatically forever**. You never need to touch them again.

**Time to set up:** 5 minutes  
**Cost:** FREE (cron-job.org free tier)  
**Result:** Fully automated trial warnings + backups

---

**Questions?** Check Render logs or cron-job.org dashboard for status! 🎯
