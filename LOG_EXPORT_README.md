# 📊 Log Export - Simple Database Export

## Quick Start

Run this one command to export all logs:

```bash
python3 export_all_logs.py
```

## What It Does

1. **Finds all log files** in your project (`.cursor/debug.log`, `.cursor/error.log`, etc.)
2. **Exports to database-ready format** (NDJSON - one JSON per line)
3. **Creates database schema** (SQL file for easy import)
4. **Generates human-readable version** (pretty JSON)

## Output Files

- **`all_logs_export.jsonl`** - Database-ready format (NDJSON)
  - One JSON object per line
  - Easy to import into any database
  - Can be streamed/processed line by line

- **`all_logs_export_pretty.json`** - Human-readable format
  - Pretty-printed JSON
  - Easy to review in any text editor
  - Contains all logs in nested structure

- **`logs_database_schema.sql`** - Database schema
  - PostgreSQL and SQLite compatible
  - Ready to run to create the logs table
  - Includes indexes for fast queries

## Importing into Database

### PostgreSQL
```sql
-- 1. Create the table
\i logs_database_schema.sql

-- 2. Import the logs (example)
COPY app_logs(timestamp, log_type, message, location, data, source_file, source_line)
FROM 'all_logs_export.jsonl' (FORMAT json);
```

### SQLite
```bash
# 1. Create the table
sqlite3 logs.db < logs_database_schema.sql

# 2. Import using Python script (recommended)
python3 -c "
import json, sqlite3
conn = sqlite3.connect('logs.db')
cursor = conn.cursor()
with open('all_logs_export.jsonl') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') != 'export_metadata':
            cursor.execute('''
                INSERT INTO app_logs (timestamp, log_type, message, location, data, source_file, source_line)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp'),
                data.get('log_type') or data.get('error_type'),
                data.get('message') or data.get('raw_text'),
                data.get('location'),
                json.dumps(data.get('data', {})),
                data.get('_source_file'),
                data.get('_source_line')
            ))
conn.commit()
"
```

### MongoDB
```javascript
// Import NDJSON directly
mongoimport --db app_logs --collection logs --file all_logs_export.jsonl --jsonArray
```

## Log Format

Each log entry contains:
- `timestamp` - When the log was created
- `log_type` - Type of log (error, debug, info, etc.)
- `message` - Log message
- `location` - Where in code (file:line or endpoint)
- `data` - Additional structured data (JSON)
- `source_file` - Original log file path
- `source_line` - Line number in source file
- `session_id`, `run_id`, `hypothesis_id` - Debug session info (if present)

## When Logs Are Empty

If you see "0 log entries", it means:
- No log files exist yet (app hasn't run)
- Logs are written to a different location
- Logs were cleared

**To generate logs:**
1. Run your app
2. Use it normally (errors/debug events will create logs)
3. Run `export_all_logs.py` again

## That's It!

Simple, clean, database-ready. Just run the script and you're done.

