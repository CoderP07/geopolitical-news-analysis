from http.client import CONFLICT
import os

import psycopg2
import json
from models import (
    EventSummary,
    NormalizedArticle,
    ClassificationResult,
    Batch,
    BatchAnalysis,
)


def get_connection():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


def get_latest_batch_run_id() -> str | None:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT run_id
    FROM batches
    WHERE run_id IS NOT NULL
    ORDER BY created_at DESC, id DESC
    LIMIT 1;
    """

    cur.execute(query)
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return None

    return row[0]


def insert_normalized_articles(articles: list[NormalizedArticle]):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO normalized_articles (
        source_name,
        title,
        url,
        published_at,
        content,
        original_snippet,
        has_full_content,
        is_valid,
        invalid_reasons
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (url) DO NOTHING;
    """

    for a in articles:
        cur.execute(
            query,
            (
                a.source_name,
                a.title,
                a.url,
                a.published_at,
                a.content,
                a.original_snippet,
                a.has_full_content,
                a.is_valid,
                json.dumps(a.invalid_reasons),
            ),
        )
    conn.commit()
    cur.close()
    conn.close()


def load_normalized_articles_for_classification() -> list[NormalizedArticle]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
        na.id,
        na.source_name,
        na.title,
        na.url,
        TO_CHAR(na.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS published_at,
        na.content,
        na.original_snippet,
        na.has_full_content,
        na.is_valid,
        na.invalid_reasons
    FROM normalized_articles na
    LEFT JOIN classification_results cr
        ON cr.normalized_article_id = na.id
    WHERE na.is_valid = TRUE
      AND cr.id IS NULL
    ORDER BY na.published_at ASC;
    """

    cur.execute(query)
    rows = cur.fetchall()

    articles = []
    for row in rows:
        articles.append(
            NormalizedArticle(
                id=row[0],
                source_name=row[1],
                title=row[2],
                url=row[3],
                published_at=row[4],
                content=row[5],
                original_snippet=row[6] or "",
                has_full_content=row[7],
                is_valid=row[8],
                invalid_reasons=row[9] or [],
            )
        )

    cur.close()
    conn.close()
    return articles


def insert_classification_results(results: list[ClassificationResult]):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO classification_results (
        normalized_article_id,
        source_name,
        title,
        url,
        published_at,
        content,
        has_full_content,
        original_snippet,
        opinion_score,
        narrative_score,
        multiactor_score,
        explanatory_score,
        opinion_reasons,
        narrative_reasons,
        multiactor_reasons,
        explanatory_reasons,
        top_two,
        final_label,
        rationale,
        llm_label,
        was_llm_used,
        classification_version
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s,
        %s, %s,
        %s, %s,
        %s
    )
    ON CONFLICT (normalized_article_id, classification_version) DO NOTHING;
    """

    for a in results:
        cur.execute(
            query,
            (
                a.normalized_article_id,
                a.source_name,
                a.title,
                a.url,
                a.published_at,
                a.content,
                a.has_full_content,
                a.original_snippet,
                a.opinion_score,
                a.narrative_score,
                a.multiactor_score,
                a.explanatory_score,
                json.dumps(a.opinion_reasons),
                json.dumps(a.narrative_reasons),
                json.dumps(a.multiactor_reasons),
                json.dumps(a.explanatory_reasons),
                json.dumps(a.top_two),
                a.final_label,
                a.rationale,
                a.llm_label,
                a.was_llm_used,
                "v1",
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def load_classification_results(
    classification_version: str = "v1",
) -> list[ClassificationResult]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
        cr.id,
        cr.normalized_article_id,
        cr.source_name,
        cr.title,
        cr.url,
        cr.published_at,
        cr.content,
        cr.has_full_content,
        cr.original_snippet,
        cr.opinion_score,
        cr.narrative_score,
        cr.multiactor_score,
        cr.explanatory_score,
        cr.opinion_reasons,
        cr.narrative_reasons,
        cr.multiactor_reasons,
        cr.explanatory_reasons,
        cr.top_two,
        cr.final_label,
        cr.rationale,
        cr.llm_label,
        cr.was_llm_used,
        cr.classification_version,
        cr.created_at
    FROM classification_results cr
    WHERE cr.classification_version = %s
    ORDER BY cr.created_at ASC, cr.id ASC;
    """

    cur.execute(query, (classification_version,))
    rows = cur.fetchall()

    results = []
    for row in rows:
        results.append(
            ClassificationResult(
                id=row[0],
                normalized_article_id=row[1],
                source_name=row[2],
                title=row[3],
                url=row[4],
                published_at=row[5],
                content=row[6],
                has_full_content=row[7],
                original_snippet=row[8],
                opinion_score=row[9],
                narrative_score=row[10],
                multiactor_score=row[11],
                explanatory_score=row[12],
                opinion_reasons=row[13] or [],
                narrative_reasons=row[14] or [],
                multiactor_reasons=row[15] or [],
                explanatory_reasons=row[16] or [],
                top_two=row[17] or [],
                final_label=row[18],
                rationale=row[19],
                llm_label=row[20],
                was_llm_used=row[21],
                created_at=str(row[23]) if row[23] is not None else "",
            )
        )

    cur.close()
    conn.close()
    return results


def insert_batches(
    batches: list[Batch],
    run_id: str,
    classification_version: str = "v1",
    batching_version: str = "v1",
):
    conn = get_connection()
    cur = conn.cursor()

    batch_query = """
    INSERT INTO batches (
        batch_type,
        classification_version,
        batching_version,
        run_id
    )
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """

    batch_article_query = """
    INSERT INTO batch_articles (
        batch_id,
        classification_result_id,
        article_order
    )
    VALUES (%s, %s, %s);
    """

    for batch in batches:
        cur.execute(
            batch_query,
            (batch.batch_type, classification_version, batching_version, run_id),
        )
        result = cur.fetchone()

        if result is None:
            raise ValueError("Failed to insert batch (no ID returned)")

        batch_id = result[0]

        for idx, article in enumerate(batch.articles, start=1):
            if article.id is None:
                raise ValueError("ClassificationResult must have id before batching")

            cur.execute(
                batch_article_query,
                (batch_id, article.id, idx),
            )

    conn.commit()
    cur.close()
    conn.close()


def load_batches_for_analysis(
    classification_version: str = "v1",
    batching_version: str = "v1",
    run_id: str | None = None,
) -> list[Batch]:

    print("[DB] Loading pending batches for analysis")

    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
        b.id AS batch_id,
        b.run_id,
        b.batch_type,

        cr.id AS classification_result_id,
        cr.normalized_article_id,
        cr.source_name,
        cr.title,
        cr.url,
        TO_CHAR(
            cr.published_at AT TIME ZONE 'UTC',
            'YYYY-MM-DD"T"HH24:MI:SS"Z"'
        ) AS published_at,
        cr.content,
        cr.has_full_content,
        cr.original_snippet,
        cr.opinion_score,
        cr.narrative_score,
        cr.multiactor_score,
        cr.explanatory_score,
        cr.opinion_reasons,
        cr.narrative_reasons,
        cr.multiactor_reasons,
        cr.explanatory_reasons,
        cr.top_two,
        cr.final_label,
        cr.rationale,
        cr.llm_label,
        cr.was_llm_used,
        ba.article_order
    FROM batches b
    JOIN batch_articles ba
        ON ba.batch_id = b.id
    JOIN classification_results cr
        ON cr.id = ba.classification_result_id
    WHERE b.classification_version = %s
        AND b.batching_version = %s
        AND b.status = 'pending'
    """

    params: list[str] = [classification_version, batching_version]

    query += " ORDER BY b.id, ba.article_order;"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    batches_by_id: dict[int, Batch] = {}

    for row in rows:
        batch_id = row[0]
        batch_run_id = row[1]
        batch_type = row[2]

        if batch_id not in batches_by_id:
            batches_by_id[batch_id] = Batch(
                id=batch_id,
                run_id=batch_run_id,
                batch_type=batch_type,
                articles=[],
            )

        article = ClassificationResult(
            id=row[3],
            normalized_article_id=row[4],
            source_name=row[5],
            title=row[6],
            url=row[7],
            published_at=row[8],
            content=row[9],
            has_full_content=row[10],
            original_snippet=row[11],
            opinion_score=row[12],
            narrative_score=row[13],
            multiactor_score=row[14],
            explanatory_score=row[15],
            opinion_reasons=row[16] or [],
            narrative_reasons=row[17] or [],
            multiactor_reasons=row[18] or [],
            explanatory_reasons=row[19] or [],
            top_two=row[20] or [],
            final_label=row[21],
            rationale=row[22],
            llm_label=row[23],
            was_llm_used=row[24],
        )

        batches_by_id[batch_id].articles.append(article)

    cur.close()
    conn.close()

    return list(batches_by_id.values())


def insert_batch_analyses(
    analyses: list[BatchAnalysis],
    analysis_version: str = "v1",
):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO batch_analyses (
        batch_id,
        article_count,
        article_titles,
        summary,
        full_analysis,
        is_valid,
        failure_reason,
        analysis_version
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (batch_id, analysis_version)
    DO UPDATE SET
        article_count = EXCLUDED.article_count,
        article_titles = EXCLUDED.article_titles,
        summary = EXCLUDED.summary,
        full_analysis = EXCLUDED.full_analysis,
        is_valid = EXCLUDED.is_valid,
        failure_reason = EXCLUDED.failure_reason;
    """

    for analysis in analyses:
        cur.execute(
            query,
            (
                analysis.batch_id,
                analysis.article_count,
                json.dumps(analysis.article_titles),
                analysis.summary,
                json.dumps(analysis.full_analysis),
                analysis.is_valid,
                analysis.failure_reason,
                analysis_version,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def load_batches_with_analysis_for_summary(
    analysis_version: str = "v1",
    summary_version: str = "v1",
) -> list[tuple[Batch, BatchAnalysis]]:

    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
    ba.id AS batch_analysis_id,
    ba.batch_id,
    ba.article_count,
    ba.article_titles,
    ba.summary,
    ba.full_analysis,
    ba.is_valid,
    ba.failure_reason,

    b.run_id,
    b.batch_type,

    cr.id AS classification_result_id,
    cr.normalized_article_id,
    cr.source_name,
    cr.title,
    cr.url,
    TO_CHAR(
        cr.published_at AT TIME ZONE 'UTC',
        'YYYY-MM-DD"T"HH24:MI:SS"Z"'
    ) AS published_at,
    cr.content,
    cr.has_full_content,
    cr.original_snippet,
    cr.opinion_score,
    cr.narrative_score,
    cr.multiactor_score,
    cr.explanatory_score,
    cr.opinion_reasons,
    cr.narrative_reasons,
    cr.multiactor_reasons,
    cr.explanatory_reasons,
    cr.top_two,
    cr.final_label,
    cr.rationale,
    cr.llm_label,
    cr.was_llm_used,

    barts.article_order
    FROM batch_analyses ba
    JOIN batches b
        ON b.id = ba.batch_id
    JOIN batch_articles barts
        ON barts.batch_id = b.id
    JOIN classification_results cr
        ON cr.id = barts.classification_result_id
    LEFT JOIN event_summaries es
        ON es.batch_analysis_id = ba.id
        AND es.summary_version = %s
    WHERE ba.analysis_version = %s
    AND ba.is_valid = TRUE
    AND b.status = 'analyzed'
    AND es.id IS NULL
    """

    params: list[str] = [summary_version, analysis_version]

    query += " ORDER BY ba.id, barts.article_order;"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    grouped: dict[int, tuple[Batch, BatchAnalysis]] = {}

    for row in rows:
        batch_analysis_id = row[0]
        batch_id = row[1]
        article_count = row[2]
        article_titles = row[3] or []
        summary = row[4]
        full_analysis = row[5] or {}
        is_valid = row[6]
        failure_reason = row[7]

        batch_run_id = row[8]
        batch_type = row[9]

        if batch_analysis_id not in grouped:
            batch = Batch(
                id=batch_id,
                run_id=batch_run_id,
                batch_type=batch_type,
                articles=[],
            )

            analysis = BatchAnalysis(
                id=batch_analysis_id,
                batch_id=batch_id,
                batch_type=batch_type,
                article_count=article_count,
                article_titles=article_titles,
                summary=summary,
                full_analysis=full_analysis,
                is_valid=is_valid,
                failure_reason=failure_reason,
            )

            grouped[batch_analysis_id] = (batch, analysis)

        article = ClassificationResult(
            id=row[10],
            normalized_article_id=row[11],
            source_name=row[12],
            title=row[13],
            url=row[14],
            published_at=row[15],
            content=row[16],
            has_full_content=row[17],
            original_snippet=row[18],
            opinion_score=row[19],
            narrative_score=row[20],
            multiactor_score=row[21],
            explanatory_score=row[22],
            opinion_reasons=row[23] or [],
            narrative_reasons=row[24] or [],
            multiactor_reasons=row[25] or [],
            explanatory_reasons=row[26] or [],
            top_two=row[27] or [],
            final_label=row[28],
            rationale=row[29],
            llm_label=row[30],
            was_llm_used=row[31],
        )

        grouped[batch_analysis_id][0].articles.append(article)

    cur.close()
    conn.close()

    return list(grouped.values())


def insert_event_summaries(
    summaries: list[EventSummary],
    summary_version: str = "v1",
):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO event_summaries (
            batch_analysis_id,
            batch_type,
            headline,
            deck,
            website_summary,
            key_points,
            source_titles,
            source_links,
            is_valid,
            failure_reason,
            raw_output,
            summary_version
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (batch_analysis_id, summary_version)
        DO UPDATE SET
            batch_type = EXCLUDED.batch_type,
            headline = EXCLUDED.headline,
            deck = EXCLUDED.deck,
            website_summary = EXCLUDED.website_summary,
            key_points = EXCLUDED.key_points,
            source_titles = EXCLUDED.source_titles,
            source_links = EXCLUDED.source_links,
            is_valid = EXCLUDED.is_valid,
            failure_reason = EXCLUDED.failure_reason,
            raw_output = EXCLUDED.raw_output;
    """

    for summary in summaries:
        cur.execute(
            query,
            (
                summary.batch_analysis_id,
                summary.batch_type,
                summary.headline,
                summary.deck,
                summary.website_summary,
                json.dumps(summary.key_points),
                json.dumps(summary.source_titles),
                json.dumps(
                    [
                        {
                            "title": link.title,
                            "source": link.source,
                            "url": link.url,
                            "published_at": link.published_at,
                        }
                        for link in summary.source_links
                    ]
                ),
                summary.is_valid,
                summary.failure_reason,
                (
                    json.dumps(json.loads(summary.raw_output))
                    if summary.raw_output
                    else None
                ),
                summary_version,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def find_open_batch_id(
    batch_type: str,
    classification_version: str = "v1",
    batching_version: str = "v1",
    max_articles: int = 999,
) -> int | None:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT id
    FROM batches
    WHERE batch_type = %s
        AND classification_version = %s
        AND batching_version = %s
        AND status = 'pending'
        AND created_at >= CURRENT_DATE - INTERVAL '2 day'
    ORDER BY created_at DESC, id DESC
    LIMIT 1;
    """

    cur.execute(
        query,
        (
            batch_type,
            classification_version,
            batching_version,
        ),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row[0] if row else None


def append_articles_to_batch(
    batch_id: int,
    articles: list[ClassificationResult],
):
    conn = get_connection()
    cur = conn.cursor()

    order_query = """
    SELECT COALESCE(MAX(article_order), 0)
    FROM batch_articles
    WHERE batch_id = %s;
    """

    insert_query = """
    INSERT INTO batch_articles (
        batch_id,
        classification_result_id,
        article_order
    )
    VALUES (%s, %s, %s);
    """

    cur.execute(order_query, (batch_id,))
    result = cur.fetchone()
    if result is not None:
        start_order = result[0]
    else:
        # Handle the case where no row is found
        raise ValueError("No order found in the database")

    for idx, article in enumerate(articles, start=start_order + 1):
        if article.id is None:
            raise ValueError("ClassificationResult must have id before batching")

        cur.execute(
            insert_query,
            (
                batch_id,
                article.id,
                idx,
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
