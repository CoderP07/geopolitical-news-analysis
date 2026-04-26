import json
import psycopg2
from datetime import datetime, timezone


def get_connection():
    return psycopg2.connect(
        dbname="news_pipline",
        user="postgres",
        password="9320",
        host="localhost",
        port=5432,
    )


def latest_article_published_at(event: dict) -> str:
    published_times = []

    for source in event.get("source_links", []):
        published_at = source.get("published_at")
        if not published_at:
            continue

        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            published_times.append(dt)
        except ValueError:
            continue

    if not published_times:
        return event.get("created_at", "")

    return max(published_times).isoformat()


def write_events_to_website_table(
    events: list[dict], summary_version: str = "v1"
) -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM website_event_summaries
        WHERE summary_version = %s;
        """,
        (summary_version,),
    )

    query = """
    INSERT INTO website_event_summaries (
        event_summary_id,
        batch_analysis_id,
        batch_type,
        headline,
        deck,
        event_json,
        source_titles,
        source_links,
        summary_version,
        created_at,
        exported_at
    )
    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, NOW())
    ON CONFLICT (event_summary_id)
    DO UPDATE SET
        batch_analysis_id = EXCLUDED.batch_analysis_id,
        batch_type = EXCLUDED.batch_type,
        headline = EXCLUDED.headline,
        deck = EXCLUDED.deck,
        event_json = EXCLUDED.event_json,
        source_titles = EXCLUDED.source_titles,
        source_links = EXCLUDED.source_links,
        summary_version = EXCLUDED.summary_version,
        created_at = EXCLUDED.created_at,
        exported_at = NOW();
    """

    for event in events:
        cur.execute(
            query,
            (
                event["event_summary_id"],
                event.get("batch_analysis_id"),
                event.get("batch_type"),
                event.get("headline"),
                event.get("deck"),
                json.dumps(event),
                json.dumps(event.get("source_titles", [])),
                json.dumps(event.get("source_links", [])),
                summary_version,
                event.get("created_at"),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


TOPIC_KEYWORDS = {
    "ceasefire_diplomacy": ["ceasefire", "truce", "talks"],
    "hormuz_maritime": ["hormuz", "strait", "shipping"],
}


def detect_topic(event: dict) -> str | None:
    text = f"{event.get('headline', '')} {event.get('deck', '')}".lower()

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return topic

    return None


def dedupe_events_for_website(events: list[dict]) -> list[dict]:
    latest_by_topic = {}
    untopicized_events = []

    for event in events:
        topic = detect_topic(event)

        if topic is None:
            untopicized_events.append(event)
            continue

        current = latest_by_topic.get(topic)

        if current is None or latest_article_published_at(
            event
        ) > latest_article_published_at(current):
            latest_by_topic[topic] = event

    deduped_events = untopicized_events + list(latest_by_topic.values())

    return sorted(
        deduped_events,
        key=lambda e: datetime.fromisoformat(latest_article_published_at(e)),
        reverse=True,
    )


def load_event_summaries_for_website(summary_version: str = "v1") -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
        id,
        batch_analysis_id,
        batch_type,
        headline,
        deck,
        website_summary,
        key_points,
        source_titles,
        source_links,
        is_valid,
        raw_output,
        created_at
    FROM event_summaries
    WHERE summary_version = %s
      AND is_valid = TRUE
        AND created_at >= NOW() - INTERVAL '3 days'
    ORDER BY id ASC
    """

    cur.execute(query, (summary_version,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    events = []

    for row in rows:
        raw_output = row[10]
        parsed_raw = {}

        if raw_output:
            if isinstance(raw_output, str):
                parsed_raw = json.loads(raw_output)
            else:
                parsed_raw = raw_output

        final_json = (
            parsed_raw.get("final_json") if isinstance(parsed_raw, dict) else None
        )

        base_event = final_json if final_json else parsed_raw

        if not isinstance(base_event, dict) or not base_event:
            continue

        event_obj = {
            **base_event,
            "event_summary_id": row[0],
            "batch_analysis_id": row[1],
            "source_titles": row[7] or [],
            "source_links": row[8] or [],
            "batch_type": row[2],
            "created_at": row[11].isoformat() if row[11] else None,
        }

        events.append(event_obj)

    return events


if __name__ == "__main__":
    events = load_event_summaries_for_website(summary_version="v1")
    events = dedupe_events_for_website(events)
    write_events_to_website_table(events, summary_version="v1")
    print(f"Wrote {len(events)} events to website_event_summaries")
