import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()
app.mount("/static", StaticFiles(directory="src/analysis"), name="static")


@app.get("/")
def homepage():
    return FileResponse("src/analysis/website_card.html")


@app.get("/event_detail.html")
def event_detail():
    return FileResponse("src/analysis/event_detail.html")


# allow your frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise ValueError("DATABASE_URL is not set")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url)


@app.get("/api/events")
def get_events():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT event_json
        FROM website_event_summaries
        WHERE summary_version = %s
        ORDER BY created_at DESC, event_summary_id DESC;
    """,
        ("v1",),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [row[0] for row in rows]
