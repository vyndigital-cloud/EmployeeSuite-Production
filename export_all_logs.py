#!/usr/bin/env python3
"""
Simple Log Export Script
Exports all application logs to a database-ready format
"""

import os
import json
import glob
from datetime import datetime, timezone
from pathlib import Path

# Log file locations
LOG_PATHS = [
    '.cursor/debug.log',
    '.cursor/error.log',
    'debug.log',
    'error.log',
    'app.log',
    '*.log'
]

OUTPUT_FILE = 'all_logs_export.jsonl'  # NDJSON format - one JSON object per line
SCHEMA_FILE = 'logs_database_schema.sql'  # SQL schema for importing logs

def read_ndjson_file(filepath):
    """Read NDJSON file (one JSON object per line)"""
    logs = []
    if not os.path.exists(filepath):
        return logs
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    log_entry = json.loads(line)
                    log_entry['_source_file'] = filepath
                    log_entry['_source_line'] = line_num
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    # If it's not JSON, treat as plain text log
                    logs.append({
                        '_source_file': filepath,
                        '_source_line': line_num,
                        'raw_text': line,
                        'parse_error': str(e)
                    })
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return logs

def read_text_log(filepath):
    """Read plain text log file"""
    logs = []
    if not os.path.exists(filepath):
        return logs
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                logs.append({
                    '_source_file': filepath,
                    '_source_line': line_num,
                    'raw_text': line,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return logs

def find_all_log_files():
    """Find all log files in the project"""
    log_files = set()
    
    # Check specific paths
    for path in LOG_PATHS:
        if '*' in path:
            # Glob pattern
            matches = glob.glob(path, recursive=True)
            log_files.update(matches)
        else:
            if os.path.exists(path):
                log_files.add(path)
    
    # Also search for .log files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'venv' and d != '__pycache__']
        
        for file in files:
            if file.endswith('.log'):
                log_files.add(os.path.join(root, file))
    
    return sorted(log_files)

def export_logs():
    """Main export function"""
    print("🔍 Finding all log files...")
    log_files = find_all_log_files()
    
    if not log_files:
        print("⚠️  No log files found. Creating empty export.")
        log_files = []
    else:
        print(f"✅ Found {len(log_files)} log file(s):")
        for f in log_files:
            print(f"   - {f}")
    
    all_logs = []
    
    # Read each log file
    for log_file in log_files:
        print(f"\n📖 Reading {log_file}...")
        
        # Try as NDJSON first, then as plain text
        logs = read_ndjson_file(log_file)
        if not logs:
            logs = read_text_log(log_file)
        
        if logs:
            print(f"   ✅ Found {len(logs)} log entries")
            all_logs.extend(logs)
        else:
            print(f"   ⚠️  File is empty or unreadable")
    
    # Add metadata
    export_data = {
        'export_timestamp': datetime.now(timezone.utc).isoformat(),
        'total_log_entries': len(all_logs),
        'log_files_scanned': log_files,
        'logs': all_logs
    }
    
    # Write to NDJSON format (one JSON object per line) - database ready
    print(f"\n💾 Writing {len(all_logs)} log entries to {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Write metadata as first line
        f.write(json.dumps({
            'type': 'export_metadata',
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_log_entries': export_data['total_log_entries'],
            'log_files_scanned': export_data['log_files_scanned']
        }) + '\n')
        
        # Write each log entry as a separate line
        for log in all_logs:
            f.write(json.dumps(log, default=str) + '\n')
    
    # Also create a pretty JSON version for human review
    pretty_output = OUTPUT_FILE.replace('.jsonl', '_pretty.json')
    print(f"💾 Writing pretty version to {pretty_output}...")
    
    with open(pretty_output, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    # Create database schema
    print(f"\n📐 Creating database schema: {SCHEMA_FILE}...")
    create_database_schema(SCHEMA_FILE)
    
    print(f"\n✅ Export complete!")
    print(f"   📄 Database-ready format: {OUTPUT_FILE} (NDJSON - one JSON per line)")
    print(f"   📄 Human-readable format: {pretty_output} (Pretty JSON)")
    print(f"   📄 Database schema: {SCHEMA_FILE} (SQL for importing)")
    print(f"\n📊 Summary:")
    print(f"   - Total log entries: {len(all_logs)}")
    print(f"   - Log files scanned: {len(log_files)}")
    print(f"\n💡 To import into database:")
    print(f"   1. Run: {SCHEMA_FILE} to create the table")
    print(f"   2. Import: {OUTPUT_FILE} (one JSON object per line)")
    
    return OUTPUT_FILE, pretty_output, SCHEMA_FILE

def create_database_schema(schema_file):
    """Create SQL schema for logs table"""
    schema_sql = """-- Logs Database Schema
-- Simple, flexible schema for storing all application logs

CREATE TABLE IF NOT EXISTS app_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_type VARCHAR(50),  -- 'error', 'debug', 'info', 'warning', etc.
    message TEXT,
    location VARCHAR(255),  -- file:line or endpoint
    data JSONB,  -- Flexible JSON data (PostgreSQL) or TEXT (SQLite)
    source_file VARCHAR(255),
    source_line INTEGER,
    session_id VARCHAR(100),
    run_id VARCHAR(100),
    hypothesis_id VARCHAR(50),
    raw_text TEXT,  -- For non-JSON logs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON app_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_type ON app_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_logs_location ON app_logs(location);
CREATE INDEX IF NOT EXISTS idx_logs_session ON app_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_logs_source ON app_logs(source_file);

-- For SQLite compatibility (use TEXT instead of JSONB)
-- CREATE TABLE IF NOT EXISTS app_logs (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
--     log_type TEXT,
--     message TEXT,
--     location TEXT,
--     data TEXT,  -- JSON stored as TEXT
--     source_file TEXT,
--     source_line INTEGER,
--     session_id TEXT,
--     run_id TEXT,
--     hypothesis_id TEXT,
--     raw_text TEXT,
--     created_at TEXT DEFAULT CURRENT_TIMESTAMP
-- );
"""
    
    with open(schema_file, 'w', encoding='utf-8') as f:
        f.write(schema_sql)

if __name__ == '__main__':
    export_logs()

