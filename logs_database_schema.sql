-- Logs Database Schema
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
