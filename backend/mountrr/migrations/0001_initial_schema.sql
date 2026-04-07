-- Mountrr initial schema
-- Applied by database.py migration runner

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Core symlink tracking
CREATE TABLE IF NOT EXISTS symlinks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symlink_path TEXT UNIQUE NOT NULL,
    target_path TEXT NOT NULL,
    source TEXT CHECK(source IN ('rd', 'nzb', 'other')) DEFAULT 'other',
    status TEXT CHECK(status IN ('ok', 'broken', 'unknown')) DEFAULT 'unknown',
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_checked DATETIME,
    target_size INTEGER  -- bytes, nullable
);

-- Deletion audit log
CREATE TABLE IF NOT EXISTS deletion_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symlink_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    source TEXT,
    deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reason TEXT CHECK(reason IN ('manual', 'scan_cleanup', 'broken_cleanup', 'orphan_cleanup')),
    arr_search_triggered BOOLEAN DEFAULT FALSE,
    arr_instance TEXT,
    arr_search_result TEXT
);

-- Scan history
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    total_symlinks INTEGER,
    broken_found INTEGER,
    cleaned INTEGER DEFAULT 0,
    scan_type TEXT CHECK(scan_type IN ('full', 'quick', 'broken_only')) DEFAULT 'full'
);

-- Runtime configuration (key-value)
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Arr instance connections (used in v1.1)
CREATE TABLE IF NOT EXISTS arr_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('radarr', 'sonarr')) NOT NULL,
    url TEXT NOT NULL,
    api_key TEXT NOT NULL,
    media_paths TEXT DEFAULT '[]',  -- JSON array of /media subdirs
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_symlinks_status ON symlinks(status);
CREATE INDEX IF NOT EXISTS idx_symlinks_source ON symlinks(source);
CREATE INDEX IF NOT EXISTS idx_symlinks_last_checked ON symlinks(last_checked);
CREATE INDEX IF NOT EXISTS idx_deletion_history_deleted_at ON deletion_history(deleted_at);
CREATE INDEX IF NOT EXISTS idx_scan_history_started_at ON scan_history(started_at);
