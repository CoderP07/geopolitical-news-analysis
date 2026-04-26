from datetime import datetime, timedelta, UTC, time
from models import RawArticle, NormalizedArticle
import requests
from bs4 import BeautifulSoup
from readability import Document
import trafilatura
from db import insert_normalized_articles


def is_relevant_article(article: NormalizedArticle) -> bool:
    title = article.title.lower()
    content = article.content.lower()
    url = article.url.lower()
    text = f"{title} {content} {url}"

    iran_terms = [
        "iran",
        "iranian",
        "tehran",
    ]

    context_terms = [
        "blockade",
        "ceasefire",
        "talks",
        "sanctions",
        "nuclear",
        "war",
        "strike",
        "military",
        "diplomatic",
        "conflict",
        "negotiation",
        "negotiations",
        "seizure",
        "attack",
        "ship",
        "vessel",
        "hormuz",
        "mediat",
    ]

    explanatory_terms = [
        "why",
        "how",
        "what is",
        "what are",
        "what we know",
        "explained",
        "analysis",
        "sticking points",
        "key issues",
        "background",
        "negotiating table",
        "who’s at",
        "who's at",
        "all we know",
    ]

    title_override_phrases = [
        "what is",
        "what are",
        "what we know",
        "all we know",
        "explained",
        "analysis",
        "sticking points",
        "who’s at",
        "who's at",
        "negotiating table",
        "key issues",
        "background",
        "why",
        "how",
    ]

    high_value_terms = [
        "military",
        "strike",
        "seizure",
        "attack",
        "ship",
        "vessel",
        "hormuz",
        "blockade",
        "ceasefire",
        "nuclear",
        "negotiation",
        "negotiations",
        "talks",
    ]

    iran_hits = [term for term in iran_terms if term in text]
    context_hits = [term for term in context_terms if term in text]
    explanatory_hits = [term for term in explanatory_terms if term in text]

    print(
        f"[RELEVANCE] iran_hits={iran_hits} "
        f"context_hits={context_hits} "
        f"explanatory_hits={explanatory_hits}"
    )

    # Hard anchor: if the article is not actually about Iran, reject it.
    if not iran_hits:
        return False

    # Strong explanatory title override:
    # keep explicit explainer / analysis pieces as long as they are Iran-related.
    if any(phrase in title for phrase in title_override_phrases):
        print("[RELEVANCE PASS] title_override_explanatory")
        return True

    score = 0

    # Iran anchoring
    score += 2

    # General context evidence
    score += len(context_hits)

    # Explanatory evidence is more valuable than raw keyword count
    score += 2 * len(explanatory_hits)

    # If the title itself contains relevant context, boost strongly
    if any(term in title for term in context_terms):
        score += 2

    # If the title contains explanatory framing, boost strongly
    if any(term in title for term in explanatory_terms):
        score += 2

    # Core event-driver terms should be enough to save important event articles
    if any(term in text for term in high_value_terms):
        score += 2

    # Longer snippets often indicate richer explanatory content
    if len(article.content) >= 300:
        score += 1

    print(f"[RELEVANCE SCORE] score={score}")

    return score >= 4


def normalize_single(
    article: RawArticle,
    lower: datetime,
    upper: datetime,
) -> NormalizedArticle:
    reasons: list[str] = []

    source_name = (article.source_name or "").strip()
    title = (article.title or "").strip()
    url = (article.url or "").strip()
    content = (article.content or "").strip()

    title_lower = title.lower()
    url_lower = url.lower()
    content_lower = content.lower()

    if "live" in title_lower or "/live/" in url_lower:
        reasons.append("live_page")

    if "video" in url_lower or "/videos/" in url_lower:
        reasons.append("video_page")

    if (
        "bitcoin" in content_lower
        or "crypto" in content_lower
        or "crypto currency" in content_lower
    ):
        reasons.append("crypto_talk")

    if len(content) < 40:
        reasons.append("content_too_short")

    if not source_name:
        reasons.append("missing_source_name")

    if not title:
        reasons.append("missing_title")

    if not url:
        reasons.append("missing_url")
    else:
        if " " in url:
            reasons.append("url_contains_spaces")
        if not (url.startswith("http://") or url.startswith("https://")):
            reasons.append("url_missing_http_scheme")

    if article.published_at is None:
        reasons.append("missing_or_invalid_published_at")
        published_at_str = ""
    else:
        if article.published_at < lower or article.published_at > upper:
            reasons.append("published_at_out_of_range")
        published_at_str = article.published_at.astimezone(UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    if not content:
        reasons.append("missing_content")

    is_valid = len(reasons) == 0

    if not is_valid:
        return NormalizedArticle(
            source_name="",
            title="",
            url="",
            published_at="",
            content="",
            original_snippet="",
            has_full_content=False,
            is_valid=False,
            invalid_reasons=reasons,
        )

    return NormalizedArticle(
        source_name=source_name,
        title=title,
        url=url,
        published_at=published_at_str,
        original_snippet="",
        has_full_content=False,
        content=content,
        is_valid=True,
        invalid_reasons=[],
    )


def fetch_full_article_text(url: str) -> str | None:
    print(f"\n[FETCH] url={url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        print(f"[FETCH OK] status={response.status_code} html_chars={len(html)}")
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "http_error"
        print(f"[FETCH FAIL] status={status} url={url}")
        return None

    # Primary extractor: trafilatura
    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        extracted_len = len(extracted.strip()) if extracted else 0
        print(f"[TRAFILATURA] extracted_chars={extracted_len}")

        if extracted and extracted_len >= 400:
            print("[TRAFILATURA SUCCESS]")
            print("[TRAFILATURA PREVIEW]")
            print(extracted[:1200])
            return extracted.strip()
    except Exception as e:
        print(f"[TRAFILATURA FAIL] {type(e).__name__}: {e}")

    # Fallback: readability-lxml + BeautifulSoup
    try:
        doc = Document(html)
        article_html = doc.summary()
        soup = BeautifulSoup(article_html, "html.parser")
        text = soup.get_text("\n", strip=True)
        text_len = len(text.strip()) if text else 0
        print(f"[READABILITY] extracted_chars={text_len}")

        if text and text_len >= 400:
            print("[READABILITY SUCCESS]")
            print("[READABILITY PREVIEW]")
            print(text[:1200])
            return text.strip()
    except Exception as e:
        print(f"[READABILITY FAIL] {type(e).__name__}: {e}")

    print("[EXTRACTION FAILED] returning None")
    return None


def normalize_articles(
    raw_articles: list[RawArticle], lower: datetime, upper: datetime
) -> list[NormalizedArticle]:
    normalized = []

    for i, article in enumerate(raw_articles, start=1):
        print(f"\n================ ARTICLE {i} ================")
        print(f"[RAW TITLE] {article.title}")
        print(f"[RAW URL] {article.url}")
        print(f"[RAW CONTENT LEN] {len((article.content or '').strip())}")
        print(f"[RAW CONTENT PREVIEW] {(article.content or '').strip()[:500]}")

        norm = normalize_single(article, lower, upper)

        if not norm.is_valid:
            print(f"[DROP INVALID] reasons={norm.invalid_reasons}")
            continue

        print(f"[NORMALIZED OK] title={norm.title}")
        print(f"[NORMALIZED SNIPPET LEN] {len(norm.content)}")
        print(f"[NORMALIZED SNIPPET PREVIEW] {norm.content[:500]}")

        if not is_relevant_article(norm):
            print("[DROP IRRELEVANT]")
            continue

        print("[RELEVANT] attempting full-text fetch...")

        full_text = fetch_full_article_text(norm.url)

        norm.original_snippet = norm.content

        if full_text and len(full_text) > len(norm.content):
            norm.content = full_text
            norm.has_full_content = True
            print("[FULL TEXT SUCCESS]")
            print(f"[FULL TEXT LEN] {len(norm.content)}")
            print("[FULL TEXT PREVIEW]")
            print(norm.content[:1500])
        else:
            norm.has_full_content = False
            print("[FULL TEXT FAILED OR NOT BETTER]")
            print(f"[USING SNIPPET LEN] {len(norm.content)}")

        normalized.append(norm)

    return normalized


if __name__ == "__main__":
    from ingest_news import ingest_articles

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    lower = datetime.combine(yesterday, time(0, 0, 0), tzinfo=UTC)
    upper = datetime.combine(today, time(23, 59, 59), tzinfo=UTC)

    raw_articles = ingest_articles()
    normalized_articles = normalize_articles(raw_articles, lower, upper)
    insert_normalized_articles(normalized_articles)

    print("\n==========================================")
    print("FINAL SUMMARY")
    print("==========================================")
    print("total_raw:", len(raw_articles))
    print("normalized_kept:", len(normalized_articles))

    for i, article in enumerate(normalized_articles, start=1):
        print(f"\n---- KEPT ARTICLE {i} ----")
        print("TITLE:", article.title)
        print("SOURCE:", article.source_name)
        print("URL:", article.url)
        print("HAS FULL CONTENT:", article.has_full_content)
        print("SNIPPET LEN:", len(article.original_snippet))
        print("FINAL CONTENT LEN:", len(article.content))
        print("SNIPPET PREVIEW:")
        print(article.original_snippet[:500])
        print("FINAL CONTENT PREVIEW:")
        print(article.content[:1500])
