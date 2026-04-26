import os
import re
from .summary_quality import finalize_summary_json
from models import Batch, BatchAnalysis, EventSummary, SourceLink
from .specs import (
    EVENT_SUMMARY_PROMPT,
    EVENT_SUMMARY_SCHEMA,
)
from openai import OpenAI
import json

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY is not set")
client = OpenAI(api_key=openai_key)


def summary_content_cap_for_batch_type(batch_type: str) -> int:
    if batch_type == "multiactor":
        return 1500
    if batch_type.startswith("explanatory::"):
        return 2000
    return 1500


def clean_article_text_for_summary(text: str) -> str:
    if not text:
        return ""

    junk_patterns = [
        r"Recommended Stories.*",
        r"list of \d+ items.*",
    ]

    cleaned = text
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_summary_input(batch: Batch, analysis: BatchAnalysis) -> str:
    cap = summary_content_cap_for_batch_type(batch.batch_type)
    lines = []

    lines.append("STRUCTURED ANALYSIS:")
    lines.append(json.dumps(analysis.full_analysis, ensure_ascii=False, indent=2))

    lines.append("")
    lines.append("SOURCE ARTICLES:")

    for i, article in enumerate(batch.articles, 1):
        cleaned_content = clean_article_text_for_summary(article.content)

        print(f"[DEBUG build_summary_input] article_title={article.title}")
        print(
            f"[DEBUG build_summary_input] has_full_content={article.has_full_content}"
        )
        print(f"[DEBUG build_summary_input] raw_content_len={len(article.content)}")
        print(f"[DEBUG build_summary_input] cleaned_content_len={len(cleaned_content)}")

        lines.append(f"{i}. Title: {article.title}")
        lines.append(f"   Source: {article.source_name}")
        lines.append(f"   Published at: {article.published_at}")
        lines.append(f"   Has full content: {article.has_full_content}")
        lines.append("   Content:")
        lines.append(cleaned_content[:cap])
        lines.append("")

    return "\n".join(lines)


def summarize_event_for_website(batch: Batch, analysis: BatchAnalysis) -> EventSummary:
    assert (
        analysis.id is not None
    ), "BatchAnalysis must have id before saving event summary"

    source_links = [
        SourceLink(
            title=article.title,
            source=article.source_name,
            url=article.url,
            published_at=article.published_at,
        )
        for article in batch.articles
    ]

    if not analysis.is_valid:
        return EventSummary(
            batch_analysis_id=analysis.id,
            batch_type=batch.batch_type,
            headline="",
            deck="",
            website_summary="",
            key_points=[],
            source_titles=[article.title for article in batch.articles],
            source_links=source_links,
            is_valid=False,
            failure_reason=f"Batch analysis invalid: {analysis.failure_reason}",
            raw_output=None,
        )

    try:
        prompt_input = build_summary_input(batch, analysis)

        response = client.responses.create(
            model="gpt-5.4-mini",
            reasoning={"effort": "medium"},
            instructions=EVENT_SUMMARY_PROMPT,
            input=prompt_input,
            max_output_tokens=6000,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "event_summary",
                    "strict": True,
                    "schema": EVENT_SUMMARY_SCHEMA,
                }
            },
        )

        raw_llm_output = response.output_text
        llm_result = json.loads(raw_llm_output)

        finalization = finalize_summary_json(llm_result, client)

        if not finalization.is_valid or finalization.final_json is None:
            failure_payload = {
                "raw_llm_output": llm_result,
                "failure_reason": finalization.failure_reason
                or "summary_finalization_failed",
                "repair_attempted": finalization.repair_attempted,
                "initial_validation_issues": [
                    {
                        "path": issue.path,
                        "issue_type": issue.issue_type,
                        "message": issue.message,
                        "severity": issue.severity,
                    }
                    for issue in finalization.initial_validation.issues
                ],
                "final_validation_issues": [
                    {
                        "path": issue.path,
                        "issue_type": issue.issue_type,
                        "message": issue.message,
                        "severity": issue.severity,
                    }
                    for issue in (
                        finalization.final_validation.issues
                        if finalization.final_validation is not None
                        else []
                    )
                ],
            }

            return EventSummary(
                batch_analysis_id=analysis.id,
                batch_type=batch.batch_type,
                headline="",
                deck="",
                website_summary="",
                key_points=[],
                source_titles=[article.title for article in batch.articles],
                source_links=source_links,
                is_valid=False,
                failure_reason=finalization.failure_reason
                or "summary_finalization_failed",
                raw_output=json.dumps(failure_payload, ensure_ascii=False),
            )

        final_json = finalization.final_json
        success_payload = {
            "final_json": final_json,
            "repair_attempted": finalization.repair_attempted,
            "initial_validation_issues": [
                {
                    "path": issue.path,
                    "issue_type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                }
                for issue in finalization.initial_validation.issues
            ],
        }

        return EventSummary(
            batch_analysis_id=analysis.id,
            batch_type=batch.batch_type,
            headline=final_json["headline"],
            deck=final_json["deck"],
            website_summary=final_json["executive_summary"],
            key_points=final_json["key_points"],
            source_titles=[article.title for article in batch.articles],
            source_links=source_links,
            is_valid=True,
            failure_reason=None,
            raw_output=json.dumps(success_payload, ensure_ascii=False),
        )

    except Exception as e:
        exception_payload = {
            "failure_reason": str(e),
        }

        if "raw_llm_output" in locals():
            exception_payload["raw_llm_output"] = raw_llm_output

        return EventSummary(
            batch_analysis_id=analysis.id,
            batch_type=batch.batch_type,
            headline="",
            deck="",
            website_summary="",
            key_points=[],
            source_titles=[article.title for article in batch.articles],
            source_links=source_links,
            is_valid=False,
            failure_reason=str(e),
            raw_output=json.dumps(exception_payload, ensure_ascii=False),
        )


if __name__ == "__main__":
    from db import load_batches_with_analysis_for_summary, insert_event_summaries
    from analysis.summary_export import (
        load_event_summaries_for_website,
        write_events_to_website_table,
    )

    batch_analysis_pairs = load_batches_with_analysis_for_summary(
        analysis_version="v1",
        summary_version="v1",
    )

    print(f"Loaded {len(batch_analysis_pairs)} batch+analysis pairs from DB.")

    summaries = []

    for batch, analysis in batch_analysis_pairs:
        print("----")
        print("BATCH ID:", batch.id)
        print("RUN ID:", batch.run_id)
        print("BATCH TYPE:", batch.batch_type)

        event_summary = summarize_event_for_website(batch, analysis)
        summaries.append(event_summary)

        print(f"[EVENT SUMMARY] is_valid={event_summary.is_valid}")
        print(f"[EVENT SUMMARY] failure_reason={event_summary.failure_reason}")
        print(f"[EVENT SUMMARY] headline={event_summary.headline}")

    if summaries:
        insert_event_summaries(summaries, summary_version="v1")

        # NEW: export to frontend
        events = load_event_summaries_for_website(summary_version="v1")
        write_events_to_website_table(events)

        print(f"[EXPORT] Wrote {len(events)} events to website table")


# python -m analysis.final_summary
