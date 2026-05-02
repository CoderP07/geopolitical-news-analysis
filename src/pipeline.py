from asyncio import events
from datetime import datetime, timedelta, UTC, time, date
import os
from uuid import uuid4
import psycopg2

from ingest_news import ingest_articles
from normalize_articles import normalize_articles
from classify_articles import classify_articles

from db import (
    insert_normalized_articles,
    load_normalized_articles_for_classification,
    insert_classification_results,
    load_classification_results,
    insert_batches,
    load_batches_for_analysis,
    insert_batch_analyses,
    load_batches_with_analysis_for_summary,
    insert_event_summaries,
)

from analysis.final_summary import summarize_event_for_website
from maintenance.cleanup_old_summaries import delete_old_event_summaries

from analysis.analyze_batches import (
    get_min_articles_for_batch,
    analyze_single_batch,
    mark_batch_analyzed,
)

from analysis.summary_export import (
    get_connection,
    load_event_summaries_for_website,
    dedupe_events_for_website,
    filter_publishable_events,
    write_events_to_website_table,
)

from collections import defaultdict
from models import Batch
from assign_batches import batch_type_for_article
from db import find_open_batch_id, append_articles_to_batch, insert_batches


def get_connection():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


def get_latest_analyzed_batch_run_id(
    analysis_version: str = "v1",
) -> str | None:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT b.run_id
    FROM batch_analyses ba
    JOIN batches b
        ON b.id = ba.batch_id
    WHERE ba.analysis_version = %s
      AND b.run_id IS NOT NULL
    ORDER BY ba.created_at DESC, ba.id DESC
    LIMIT 1;
    """

    cur.execute(query, (analysis_version,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row[0] if row else None


def make_run_id() -> str:
    return f"batch_run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:6]}"


def run_pipeline():
    run_id = make_run_id()

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    lower = datetime.combine(yesterday, time(0, 0, 0), tzinfo=UTC)
    upper = datetime.combine(today, time(23, 59, 59), tzinfo=UTC)

    print("===================================")
    print("PIPELINE START")
    print("run_id:", run_id)
    print("date window:", lower, "to", upper)
    print("===================================")

    # 1. Ingest
    raw_articles = ingest_articles(lower=lower, upper=upper)
    print(f"[INGEST] raw_articles={len(raw_articles)}")

    # 2. Normalize + insert
    normalized = normalize_articles(raw_articles, lower, upper)
    insert_normalized_articles(normalized)
    print(f"[NORMALIZE] inserted_or_skipped={len(normalized)}")

    # 3. Load unclassified normalized rows from DB
    normalized_for_classification = load_normalized_articles_for_classification()
    print(f"[CLASSIFY LOAD] articles={len(normalized_for_classification)}")

    # 4. Classify + insert
    classification_results = classify_articles(normalized_for_classification)
    insert_classification_results(classification_results)
    print(f"[CLASSIFY] inserted_or_skipped={len(classification_results)}")
    if not classification_results:
        print(
            "[CLASSIFY] No new articles classified. Continuing to pending batch analysis and summary export."
        )

    # 5. Load classified rows
    newly_classified_ids = {
        result.normalized_article_id for result in classification_results
    }

    classified_articles = [
        article
        for article in load_classification_results(classification_version="v1")
        if article.normalized_article_id in newly_classified_ids
    ]

    print(f"[BATCH LOAD] newly_classified_articles={len(classified_articles)}")

    # 6. Assign newly classified articles into open pending batches
    articles_by_batch_type = defaultdict(list)

    for article in classified_articles:
        batch_type = batch_type_for_article(article)

        if batch_type is None:
            continue

        articles_by_batch_type[batch_type].append(article)

    created_batches = []

    for batch_type, articles in articles_by_batch_type.items():
        open_batch_id = find_open_batch_id(
            batch_type=batch_type,
            classification_version="v1",
            batching_version="v1",
        )

        if open_batch_id is not None:
            append_articles_to_batch(open_batch_id, articles)
            print(
                f"[BATCH APPEND] batch_id={open_batch_id} "
                f"batch_type={batch_type} added={len(articles)}"
            )
        else:
            batch = Batch(
                batch_type=batch_type,
                articles=articles,
            )
            created_batches.append(batch)

    if created_batches:
        insert_batches(
            created_batches,
            run_id=run_id,
            classification_version="v1",
            batching_version="v1",
        )
        print(f"[BATCH CREATE] batches={len(created_batches)}")
    else:
        print("[BATCH CREATE] no new batches")

    batches_for_analysis = load_batches_for_analysis(
        classification_version="v1",
        batching_version="v1",
        run_id=None,
    )

    print(f"[ANALYSIS LOAD] batches={len(batches_for_analysis)}")

    analyses = []

    for batch in batches_for_analysis:
        required = get_min_articles_for_batch(batch.batch_type)

        if required is None:
            print(f"[ANALYSIS SKIP] unsupported batch_type={batch.batch_type}")
            continue

        if len(batch.articles) < required:
            print(
                f"[ANALYSIS SKIP] batch_type={batch.batch_type} "
                f"count={len(batch.articles)} required>={required}"
            )
            continue

        analysis = analyze_single_batch(batch)
        analyses.append(analysis)

        print(
            f"[ANALYSIS DONE] batch_id={batch.id} "
            f"batch_type={batch.batch_type} valid={analysis.is_valid}"
        )

    if analyses:
        insert_batch_analyses(
            analyses,
            analysis_version="v1",
        )
        for analysis in analyses:
            if analysis.is_valid:
                mark_batch_analyzed(analysis.batch_id)

        print(f"[ANALYSIS INSERT] analyses={len(analyses)}")
    else:
        print("[ANALYSIS INSERT] no eligible analyses")

    # 9. Load only this run_id's batch analyses for final website summaries
    batch_analysis_pairs = load_batches_with_analysis_for_summary(
        analysis_version="v1",
        summary_version="v2",
    )

    print(f"[ANALYSIS LOAD] batches={len(batches_for_analysis)}")

    summaries = []

    for batch, analysis in batch_analysis_pairs:
        event_summary = summarize_event_for_website(batch, analysis)
        summaries.append(event_summary)

        print(
            f"[SUMMARY DONE] batch_id={batch.id} "
            f"batch_type={batch.batch_type} "
            f"valid={event_summary.is_valid}"
        )

    if summaries:
        insert_event_summaries(summaries, summary_version="v2")
        print(f"[SUMMARY INSERT] summaries={len(summaries)}")
    else:
        print("[SUMMARY INSERT] no summaries")

    # Delete old summaries (valid and invalid) beyond retention period to keep DB clean.
    delete_old_event_summaries(retention_days=4)

    # 10. Export valid summaries to frontend
    events = load_event_summaries_for_website(summary_version="v2")
    events = dedupe_events_for_website(events)
    events = filter_publishable_events(events)
    write_events_to_website_table(events, summary_version="v2")

    print(f"[EXPORT] wrote {len(events)} events to website_event_summaries")

    print("===================================")
    print("PIPELINE COMPLETE")
    print("run_id:", run_id)
    print("===================================")


if __name__ == "__main__":
    run_pipeline()
