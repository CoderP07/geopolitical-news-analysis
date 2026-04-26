import os

import psycopg2

from db import insert_batch_analyses
from models import Batch, BatchAnalysis
import json
from openai import OpenAI
from dataclasses import asdict


from .specs import (
    MULTIACTOR_PROMPT,
    MULTIACTOR_SCHEMA,
    EXPLANATORY_PROMPT,
    EXPLANATORY_SCHEMA,
)

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY is not set")
client = OpenAI(api_key=openai_key)


def get_connection():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


def mark_batch_analyzed(batch_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE batches
        SET status = 'analyzed'
        WHERE id = %s;
        """,
        (batch_id,),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_min_articles_for_batch(batch_type: str) -> int | None:
    if batch_type == "multiactor":
        return 3

    if batch_type.startswith("explanatory::"):
        return 2

    return None


def content_cap_for_batch_type(batch_type: str) -> int:
    if batch_type == "multiactor":
        return 3000
    if batch_type.startswith("explanatory::"):
        return 4500
    return 3000


def batch_is_eligible_for_analysis(batch: Batch) -> bool:
    min_required = get_min_articles_for_batch(batch.batch_type)
    if min_required is None:
        return False
    return len(batch.articles) >= min_required


def batch_to_prompt_input(batch: Batch) -> str:
    ordered_articles = sorted(batch.articles, key=lambda a: a.published_at)

    lines = [
        f"Batch type: {batch.batch_type}",
        "Articles:",
        "",
        "Each article includes:",
        "- Content: primary text for analysis",
        "- Has full content: whether full article text was successfully extracted",
        "- Original snippet: truncated preview from NewsAPI",
        "",
        "If Has full content = False:",
        "- Treat the article as lower-confidence evidence",
        "- Avoid strong inference based on it",
        "",
    ]
    cap = content_cap_for_batch_type(batch.batch_type)
    for i, article in enumerate(ordered_articles, start=1):
        lines.append(f"{i}. Title: {article.title}")
        lines.append(f"   Source: {article.source_name}")
        lines.append(f"   Published at: {article.published_at}")
        lines.append(f"   URL: {article.url}")
        lines.append(f"   Final label: {article.final_label}")
        lines.append(f"   Rationale: {article.rationale}")
        lines.append("   Content:")
        lines.append(article.content[:cap])  # cap to avoid token blowup
        lines.append(f"   Has full content: {article.has_full_content}")
        lines.append(f"   Original snippet:")
        lines.append(article.original_snippet[:500])

    return "\n".join(lines)


def get_batch_analysis_spec(batch_type: str) -> tuple[str, dict]:
    if batch_type == "multiactor":
        return MULTIACTOR_PROMPT, MULTIACTOR_SCHEMA

    if batch_type.startswith("explanatory::"):
        return EXPLANATORY_PROMPT, EXPLANATORY_SCHEMA

    raise ValueError(f"Unsupported batch type: {batch_type}")


def call_batch_analysis_llm(batch: Batch) -> dict:
    prompt_template, schema = get_batch_analysis_spec(batch.batch_type)
    prompt_input = batch_to_prompt_input(batch)

    safe_name = batch.batch_type.replace("::", "__")
    response = client.responses.create(
        model="gpt-5.4-mini",
        reasoning={"effort": "medium"},
        instructions=prompt_template,  # static, no formatting
        input=prompt_input,  # all dynamic content here
        text={
            "format": {
                "type": "json_schema",
                "name": f"{safe_name}_batch_analysis",
                "strict": True,
                "schema": schema,
            }
        },
    )
    print("=== PROMPT INPUT ===")
    print(prompt_input[:2000])
    print("====================")
    return json.loads(response.output_text)


def analyze_single_batch(batch: Batch) -> BatchAnalysis:
    assert batch.id is not None, "Batch must have id before analysis"
    try:
        llm_result = call_batch_analysis_llm(batch)

        return BatchAnalysis(
            batch_id=batch.id,
            batch_type=batch.batch_type,
            article_count=len(batch.articles),
            article_titles=[article.title for article in batch.articles],
            summary=llm_result.get("summary", {}).get("instant", ""),
            full_analysis=llm_result,
            is_valid=True,
            failure_reason=None,
        )

    except Exception as e:
        return BatchAnalysis(
            batch_id=batch.id,
            batch_type=batch.batch_type,
            article_count=len(batch.articles),
            article_titles=[article.title for article in batch.articles],
            summary="",
            full_analysis={},
            is_valid=False,
            failure_reason=str(e),
        )


if __name__ == "__main__":
    from db import load_batches_for_analysis, insert_batch_analyses
    from dataclasses import asdict
    import json

    batches = load_batches_for_analysis(
        classification_version="v1",
        batching_version="v1",
    )

    print(f"Loaded {len(batches)} batches from DB.")

    analyses = []

    for batch in batches:
        print("----")
        print("BATCH ID:", batch.id)
        print("RUN ID:", batch.run_id)
        print("BATCH TYPE:", batch.batch_type)
        print("COUNT:", len(batch.articles))

        required = get_min_articles_for_batch(batch.batch_type)

        if required is None:
            print(f"[SKIP] batch_type={batch.batch_type} unsupported")
            continue

        if len(batch.articles) < required:
            print(
                f"[SKIP] batch_type={batch.batch_type} "
                f"count={len(batch.articles)} required>={required}"
            )
            continue

        analysis = analyze_single_batch(batch)
        analyses.append(analysis)

        print(json.dumps(asdict(analysis), indent=2, ensure_ascii=False))

    print("ANALYSES TO INSERT:", [a.batch_id for a in analyses])

    if analyses:
        insert_batch_analyses(
            analyses,
            analysis_version="v1",
        )
    else:
        print("[INFO] No eligible batches to analyze.")

# cd "C:\GitHub\Project Competition\src"
# python -m analysis.analyze_batches
