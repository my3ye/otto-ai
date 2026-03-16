-- Article version history — full snapshot on every content save
-- Auto-snapshot previous state before PATCH updates
-- Max 50 versions per article (enforced in application layer)

CREATE TABLE IF NOT EXISTS article_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id      UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    note            TEXT,           -- optional label e.g. "Pre-publish draft", "Major rewrite"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_article_versions_article_version
    ON article_versions(article_id, version_number);

CREATE INDEX IF NOT EXISTS idx_article_versions_article_created
    ON article_versions(article_id, created_at DESC);
