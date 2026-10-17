CREATE TABLE IF NOT EXISTS graphic_book_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    passage_id TEXT NOT NULL REFERENCES passages(id),
    kind TEXT NOT NULL CHECK (kind IN ('new', 'replacement')),
    source_sha256 TEXT NOT NULL,
    image_s3_key TEXT NOT NULL,
    image_sha256 TEXT NOT NULL,
    byte_count BIGINT NOT NULL CHECK (byte_count > 0),
    original_sha256 TEXT,
    source_commit TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'rejected')),
    reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS graphic_book_results_passage_idx
    ON graphic_book_results(passage_id, imported_at);

CREATE TABLE IF NOT EXISTS graphic_book_result_files (
    result_id TEXT NOT NULL REFERENCES graphic_book_results(result_id),
    path TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    byte_count BIGINT NOT NULL CHECK (byte_count > 0),
    PRIMARY KEY (result_id, path)
);

CREATE TABLE IF NOT EXISTS graphic_book_pages (
    passage_id TEXT PRIMARY KEY REFERENCES passages(id),
    image_s3_key TEXT NOT NULL,
    image_sha256 TEXT NOT NULL,
    byte_count BIGINT NOT NULL CHECK (byte_count > 0),
    source_sha256 TEXT,
    result_id TEXT REFERENCES graphic_book_results(result_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
