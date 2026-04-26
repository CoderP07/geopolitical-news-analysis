import os
import psycopg2


def get_connection():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


conn = get_connection()
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS normalized_articles (
    id SERIAL PRIMARY KEY,
    source_name TEXT,
    title TEXT,
    url TEXT UNIQUE,
    published_at TIMESTAMP,
    content TEXT,
    original_snippet TEXT,
    has_full_content BOOLEAN,
    is_valid BOOLEAN,
    invalid_reasons JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS classification_results (
    id SERIAL PRIMARY KEY,
    normalized_article_id INT,
    source_name TEXT,
    title TEXT,
    url TEXT,
    published_at TEXT,
    content TEXT,
    has_full_content BOOLEAN,
    original_snippet TEXT,
    opinion_score FLOAT,
    narrative_score FLOAT,
    multiactor_score FLOAT,
    explanatory_score FLOAT,
    opinion_reasons JSONB,
    narrative_reasons JSONB,
    multiactor_reasons JSONB,
    explanatory_reasons JSONB,
    top_two JSONB,
    final_label TEXT,
    rationale TEXT,
    llm_label TEXT,
    was_llm_used BOOLEAN,
    classification_version TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS batches (
    id SERIAL PRIMARY KEY,
    batch_type TEXT,
    classification_version TEXT,
    batching_version TEXT,
    run_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS batch_articles (
    id SERIAL PRIMARY KEY,
    batch_id INT,
    classification_result_id INT,
    article_order INT
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS batch_analyses (
    id SERIAL PRIMARY KEY,
    batch_id INT,
    article_count INT,
    article_titles JSONB,
    summary TEXT,
    full_analysis JSONB,
    is_valid BOOLEAN,
    failure_reason TEXT,
    analysis_version TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS event_summaries (
    id SERIAL PRIMARY KEY,
    batch_analysis_id INT,
    batch_type TEXT,
    headline TEXT,
    deck TEXT,
    website_summary TEXT,
    key_points JSONB,
    source_titles JSONB,
    source_links JSONB,
    is_valid BOOLEAN,
    failure_reason TEXT,
    raw_output JSONB,
    summary_version TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""
)

cur.execute(
    """
CREATE TABLE IF NOT EXISTS website_event_summaries (
    id SERIAL PRIMARY KEY,
    event_summary_id INT,
    batch_analysis_id INT,
    batch_type TEXT,
    headline TEXT,
    deck TEXT,
    event_json JSONB,
    source_titles JSONB,
    source_links JSONB,
    summary_version TEXT,
    created_at TIMESTAMP,
    exported_at TIMESTAMP
);
"""
)

conn.commit()
cur.close()
conn.close()

print("DB initialized")
