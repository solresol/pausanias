PRAGMA foreign_keys = ON;
PRAGMA journal_mode = DELETE;
CREATE TABLE metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL,
    generation INTEGER NOT NULL,
    exported_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE passages (
    id TEXT PRIMARY KEY,
    book INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    section INTEGER NOT NULL,
    greek_text TEXT NOT NULL
);
CREATE TABLE translations (
    passage_id TEXT PRIMARY KEY REFERENCES passages(id),
    greek_text TEXT NOT NULL,
    english_translation TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    source_sha256 TEXT NOT NULL
);
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'aborted', 'expired')),
    replacement_draw REAL CHECK (replacement_draw >= 0 AND replacement_draw < 1),
    replacement_passage_id TEXT REFERENCES passages(id),
    replacement_outcome TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE active_worker (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    token TEXT NOT NULL UNIQUE,
    owner TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('cloud', 'raksasa')),
    started_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    run_id TEXT REFERENCES runs(run_id)
);
CREATE TABLE results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    passage_id TEXT NOT NULL REFERENCES passages(id),
    kind TEXT NOT NULL CHECK (kind IN ('new', 'replacement')),
    source_sha256 TEXT NOT NULL,
    image_s3_key TEXT NOT NULL,
    image_sha256 TEXT NOT NULL,
    byte_count INTEGER NOT NULL CHECK (byte_count > 0),
    original_sha256 TEXT,
    source_commit TEXT NOT NULL,
    created_at TEXT NOT NULL,
    import_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (import_status IN ('pending', 'accepted', 'rejected')),
    import_reason TEXT NOT NULL DEFAULT '',
    UNIQUE (run_id, passage_id)
);
CREATE TABLE result_files (
    result_id TEXT NOT NULL REFERENCES results(result_id),
    path TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_count INTEGER NOT NULL CHECK (byte_count > 0),
    PRIMARY KEY (result_id, path)
);
CREATE TABLE illustrations (
    passage_id TEXT PRIMARY KEY REFERENCES passages(id),
    image_s3_key TEXT NOT NULL,
    image_sha256 TEXT NOT NULL,
    byte_count INTEGER NOT NULL,
    source_sha256 TEXT,
    result_id TEXT
);
