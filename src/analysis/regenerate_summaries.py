from db import load_batches_with_analysis_for_summary, insert_event_summaries
from analysis.final_summary import summarize_event_for_website
from analysis.summary_export import (
    load_event_summaries_for_website,
    dedupe_events_for_website,
    write_events_to_website_table,
)


def regenerate_website_summaries():
    SUMMARY_VERSION = "v2"

    pairs = load_batches_with_analysis_for_summary(
        analysis_version="v1",
        summary_version=SUMMARY_VERSION,
    )

    TARGET_ANALYSIS_IDS = {7, 8}

    pairs = [
        (batch, analysis)
        for batch, analysis in pairs
        if analysis.id in TARGET_ANALYSIS_IDS
    ]

    print(f"[FILTERED PAIRS] {len(pairs)}")

    if not pairs:
        print(
            "[STOP] No matching batch analyses found. Check TARGET_ANALYSIS_IDS or summary_version."
        )
        return

    summaries = []
    for i, (batch, analysis) in enumerate(pairs, start=1):
        print(
            f"[REGENERATE] {i}/{len(pairs)} batch_id={batch.id} analysis_id={analysis.id}"
        )
        event_summary = summarize_event_for_website(batch, analysis)
        print(
            f"[SUMMARY] valid={event_summary.is_valid} failure={event_summary.failure_reason}"
        )
        summaries.append(event_summary)

    print(f"[INSERT] summaries={len(summaries)}")
    insert_event_summaries(summaries, summary_version=SUMMARY_VERSION)

    events = load_event_summaries_for_website(summary_version=SUMMARY_VERSION)
    print(f"[LOAD WEBSITE EVENTS] events={len(events)}")

    events = dedupe_events_for_website(events)
    print(f"[DEDUPE] events={len(events)}")

    write_events_to_website_table(events, summary_version=SUMMARY_VERSION)
    print("[DONE] wrote website_event_summaries")


if __name__ == "__main__":
    regenerate_website_summaries()
