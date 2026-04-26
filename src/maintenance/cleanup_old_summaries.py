from datetime import datetime, UTC

from db import get_connection


def delete_old_event_summaries(retention_days: int = 4) -> int:
    conn = get_connection()
    cur = conn.cursor()

    query = """
    DELETE FROM event_summaries
    WHERE created_at < NOW() - (%s || ' days')::interval
    RETURNING id;
    """

    cur.execute(query, (retention_days,))
    deleted = cur.fetchall()

    conn.commit()
    cur.close()
    conn.close()

    return len(deleted)


if __name__ == "__main__":
    deleted_count = delete_old_event_summaries(retention_days=4)
    print(f"[CLEANUP] deleted_old_event_summaries={deleted_count}")
