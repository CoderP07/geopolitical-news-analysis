from models import ClassificationResult, Batch
from typing import List, Dict
from datetime import datetime, date


from collections import defaultdict

EXPLANATORY_SUBTYPE_RULES = {
    "ceasefire_diplomacy": {
        "title_terms": [
            "ceasefire",
            "truce",
            "talks",
            "negotiations",
            "deal",
            "agreement",
            "extension",
            "mediated",
            "peace talks",
        ],
        "content_terms": [
            "negotiator",
            "delegation",
            "mediation",
            "terms of the deal",
            "sticking points",
            "conditions",
            "diplomatic",
            "talks stalled",
            "talks resumed",
            "ceasefire extension",
        ],
    },
    "hormuz_maritime": {
        "title_terms": [
            "hormuz",
            "strait",
            "shipping",
            "tanker",
            "vessel",
            "blockade",
            "naval",
        ],
        "content_terms": [
            "strait of hormuz",
            "shipping lanes",
            "blockade",
            "naval forces",
            "vessel seizure",
            "tanker",
            "cargo ship",
            "maritime",
            "port access",
            "transit control",
        ],
    },
    "energy_economic_shock": {
        "title_terms": [
            "oil",
            "prices",
            "energy",
            "markets",
            "inflation",
            "costs",
            "aviation",
            "supply",
        ],
        "content_terms": [
            "oil prices",
            "brent crude",
            "fuel",
            "jet fuel",
            "energy markets",
            "import costs",
            "supply chain",
            "inflation",
            "price shock",
            "economic impact",
        ],
    },
    "regional_spillover": {
        "title_terms": [
            "lebanon",
            "hezbollah",
            "gaza",
            "syria",
            "iraq",
            "militia",
            "proxy",
            "strikes",
            "retaliation",
        ],
        "content_terms": [
            "hezbollah",
            "southern lebanon",
            "gaza",
            "syria",
            "iraq",
            "militia groups",
            "proxy forces",
            "retaliation",
            "cross-border",
            "regional escalation",
        ],
    },
    "domestic_iran_pressure": {
        "title_terms": [
            "iran economy",
            "shortages",
            "blackouts",
            "protests",
            "unrest",
        ],
        "content_terms": [
            "domestic pressure",
            "economic strain",
            "shortages",
            "power outages",
            "protests",
            "internal unrest",
            "currency",
            "inflation inside iran",
            "daily life",
        ],
    },
    "international_response": {
        "title_terms": [
            "europe",
            "uk",
            "britain",
            "france",
            "germany",
            "un",
            "nato",
            "coalition",
            "sanctions",
        ],
        "content_terms": [
            "european response",
            "international coalition",
            "sanctions",
            "diplomatic pressure",
            "naval mission",
            "foreign policy",
            "un resolution",
            "aid",
        ],
    },
    "glossary_terms": {
        "title_terms": [
            "what is",
            "explained",
            "glossary",
            "terms",
            "meanings",
        ],
        "content_terms": [
            "refers to",
            "definition",
            "means",
            "used to describe",
            "term",
        ],
    },
}


def explanatory_subtype_for_article(article: ClassificationResult) -> str:
    title = (article.title or "").lower()
    content = (article.content or "").lower()

    best_label = "misc_explanatory"
    best_score = 0

    subtype_score_adjustments = {
        "hormuz_maritime": +1,
        "energy_economic_shock": -1,
    }

    for subtype, rules in EXPLANATORY_SUBTYPE_RULES.items():
        score = 0

        for term in rules["title_terms"]:
            if term in title:
                score += 3

        for term in rules["content_terms"]:
            if term in content:
                score += 1

        score += subtype_score_adjustments.get(subtype, 0)

        if score > best_score:
            best_score = score
            best_label = subtype

    if best_score < 3:
        return "misc_explanatory"

    return best_label


def batch_type_for_article(article: ClassificationResult) -> str | None:
    if article.final_label == "multiactor":
        return "multiactor"

    if article.final_label == "explanatory":
        subtype = explanatory_subtype_for_article(article)
        return f"explanatory::{subtype}"

    return None


def classification_matches_day(
    article: ClassificationResult,
    target_day: date,
) -> bool:
    print(f"[DEBUG] article.id={article.id} created_at={article.created_at}")

    if not article.created_at:
        return False

    created_day = datetime.fromisoformat(str(article.created_at)).date()
    return created_day == target_day


def assign_batches(
    classified_articles: List[ClassificationResult],
    target_day: date,
) -> list[Batch]:
    batches_by_type: Dict[str, Batch] = {}

    filtered_articles = [
        article
        for article in classified_articles
        if classification_matches_day(article, target_day)
    ]

    print(f"Filtered to {len(filtered_articles)} articles for {target_day.isoformat()}")

    for article in filtered_articles:
        batch_type = batch_type_for_article(article)

        if batch_type is None:
            continue

        if batch_type not in batches_by_type:
            batches_by_type[batch_type] = Batch(batch_type=batch_type)

        batches_by_type[batch_type].articles.append(article)

    return list(batches_by_type.values())


if __name__ == "__main__":
    from db import load_classification_results, insert_batches
    from datetime import datetime, UTC, date
    from uuid import uuid4

    run_id = (
        f"batch_run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:6]}"
    )

    classified_articles = load_classification_results(classification_version="v1")

    print(f"Loaded {len(classified_articles)} classified articles from DB.")

    target_day = datetime.now(UTC).date()

    batches = assign_batches(classified_articles, target_day=target_day)

    print(f"Batching only classification rows from day: {target_day.isoformat()}")

    for batch in batches:
        print("----")
        print("BATCH TYPE:", batch.batch_type)
        print("COUNT:", len(batch.articles))
        for article in batch.articles:
            print(
                "-",
                article.title,
                "->",
                article.final_label,
                "| created_at =",
                article.created_at,
            )

    insert_batches(
        batches,
        classification_version="v1",
        batching_version="v1",
        run_id=run_id,
    )
