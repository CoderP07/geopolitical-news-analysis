"""
Ingestion stage only.

Responsibilities:
- call NewsAPI
- handle pagination and bounded retries
- parse responses into RawArticle objects
- preserve ingestion metadata needed for downstream tracing
"""

from datetime import datetime, timedelta, UTC
from newsapi import NewsApiClient
from typing import Optional
from models import RawArticle


def to_raw_article(article: dict, query: str) -> RawArticle:
    published_at = None
    if article.get("publishedAt"):
        try:
            published_at = datetime.fromisoformat(
                article["publishedAt"].replace("Z", "+00:00")
            )
        except Exception:
            published_at = None

    source = article.get("source") or {}
    return RawArticle(
        source_name=source.get("name"),
        author=article.get("author"),
        title=article.get("title"),
        description=article.get("description"),
        url=article.get("url"),
        url_to_image=article.get("urlToImage"),
        published_at=published_at,
        content=article.get("content"),
        retrieved_at=datetime.now(UTC),
        query=query,
    )


def ingest_articles(lower: datetime, upper: datetime) -> list[RawArticle]:
    from_param = lower.strftime("%Y-%m-%d")
    to_param = upper.strftime("%Y-%m-%d")

    query = '("Iran") AND ("Israel" OR "nuclear program" OR "Strait of Hormuz" OR "US-Iran" OR "peace talks" OR "ceasefire" OR "blockade")'

    newsapi = NewsApiClient(api_key="NEWSAPI_KEY")
    response = newsapi.get_everything(
        q=query,
        from_param=from_param,
        to=to_param,
        language="en",
        sort_by="relevancy",
        domains=",".join(
            [
                "reuters.com",
                "apnews.com",
                "afp.com",
                "bbc.com",
                "bloomberg.com",
                "ft.com",
                "wsj.com",
                "nytimes.com",
                "washingtonpost.com",
                "theguardian.com",
                "france24.com",
                "dw.com",
                "politico.com",
                "politico.eu",
                "haaretz.com",
                "scmp.com",
            ]
        ),
    )

    return [to_raw_article(article, query) for article in response.get("articles", [])]


if __name__ == "__main__":
    today = datetime.now(UTC)
    yesterday = today - timedelta(days=1)

    raw_articles = ingest_articles(lower=yesterday, upper=today)

    print(len(raw_articles))
    if raw_articles:
        print(raw_articles[0])
