-- Universal Engineering Augmentation Event Log Schema
-- Global engineering OS event tracking

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    project TEXT,
    event_type TEXT NOT NULL,
    stage TEXT,
    tool TEXT,
    detail TEXT,
    duration_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    candidate_id TEXT,
    verification_result TEXT,
    skill_name TEXT,
    success BOOLEAN DEFAULT 1,
    error TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    project TEXT,
    task_type TEXT NOT NULL,
    description TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    result TEXT,
    verification_level TEXT,
    files_changed TEXT,
    risk_level TEXT
);

CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    project TEXT,
    problem TEXT,
    approach TEXT,
    worktree_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    test_result TEXT,
    verification_result TEXT,
    selected BOOLEAN DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    name TEXT PRIMARY KEY,
    project TEXT,
    category TEXT,
    description TEXT,
    preconditions TEXT,
    verification_level TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_used DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    project TEXT,
    level TEXT NOT NULL,
    checks TEXT,
    passed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    duration_ms INTEGER,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS architecture_map (
    project TEXT,
    module TEXT,
    file_path TEXT,
    module_type TEXT,
    event_producers TEXT,
    event_consumers TEXT,
    dependencies TEXT,
    invariants TEXT,
    last_verified DATETIME,
    PRIMARY KEY (project, module)
);

CREATE INDEX IF NOT EXISTS idx_events_project ON events(project);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project);
CREATE INDEX IF NOT EXISTS idx_candidates_project ON candidates(project);

-- Provenance tracking (Feynman evidence lineage)
CREATE TABLE IF NOT EXISTS provenance (
    record_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    git_sha TEXT,
    git_branch TEXT,
    timestamp REAL NOT NULL,
    specialist TEXT,
    specialist_hash TEXT,
    tool TEXT NOT NULL,
    evidence_chain TEXT,
    decision TEXT,
    outcome TEXT,
    verification_level TEXT DEFAULT 'standard',
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_provenance_file ON provenance(file_path);
CREATE INDEX IF NOT EXISTS idx_provenance_specialist ON provenance(specialist);
CREATE INDEX IF NOT EXISTS idx_provenance_timestamp ON provenance(timestamp);
