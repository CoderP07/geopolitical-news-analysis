from models import NormalizedArticle, SupportScore, RuleSupport, ClassificationResult
from openai import OpenAI
import json
from db import insert_classification_results

client = OpenAI(api_key="OPENAI_API_KEY")


def call_classification_llm(
    article: NormalizedArticle,
    support: RuleSupport,
    top_two: list[tuple[str, int]],
) -> dict:
    candidate_labels = [label for label, _score in top_two]

    instructions = """You are classifying one news article into exactly one of the following labels:
    - opinion
    - multiactor
    - explanatory
    - narrative

    You must classify based on the article's PRIMARY PURPOSE, not on surface keywords, not on the mere presence of multiple actors, and not on the title alone.

    Your goal is to identify what the article is fundamentally doing for the reader.

    ---

    DEFINITIONS

    OPINION:
    The article's primary purpose is to argue, persuade, or express a viewpoint.
    It advances judgments, recommendations, or positions about what should be done or what is good, bad, justified, unjustified, wise, or foolish.

    EXPLANATORY:
    The article's primary purpose is to explain why something happened, how something works, what the key issues are, who the relevant actors are, or what the consequences mean.
    It focuses on causes, mechanisms, background, structure, implications, profiles, issue breakdowns, or interpretation.

    MULTIACTOR:
    The article's primary purpose is to report direct interaction between multiple distinct actors such as states, leaders, organizations, or armed groups.
    These interactions include negotiation, retaliation, coordination, confrontation, diplomacy, bargaining, threats, or responses.
    The interaction itself must be the core story.

    NARRATIVE:
    The article's primary purpose is to recount events or developments that happened.
    It reports actions over time without primarily explaining deeper causes, structures, implications, or sustained actor-to-actor interaction.

    ---

    CORE DECISION PRINCIPLE

    Classify based on the DOMINANT JOURNALISTIC FUNCTION of the article.

    Ask:
    What is the reader mainly getting from this piece?

    - If the reader is mainly getting explanation, interpretation, breakdown, context, profiles, or implications → EXPLANATORY
    - If the reader is mainly getting reporting on active back-and-forth between actors → MULTIACTOR
    - If the reader is mainly getting a sequence of events without deeper explanation → NARRATIVE
    - If the reader is mainly getting argument or advocacy → OPINION

    ---

    EXPLANATORY OVERRIDE RULE

    Choose EXPLANATORY when interaction between actors is present but serves mainly as context for explanation.

    This includes articles whose main purpose is to:
    - explain market or economic effects
    - explain broader consequences or implications
    - explain sticking points in negotiations
    - explain what is known so far and why it matters
    - explain background, structure, or unresolved issues
    - explain causes, mechanisms, or constraints

    If the article is organized around explanation, breakdown, background, or implications, choose EXPLANATORY even if multiple actors are interacting.

    Examples of EXPLANATORY patterns:
    - "what we know"
    - "all we know"
    - "what this means"
    - "why it matters"
    - "key sticking points"
    - "who's at the negotiating table"
    - "what happened and why it matters"
    - articles explaining market movements, oil prices, diplomatic structure, or issue breakdowns

    ---

    MULTIACTOR STRICT RULE

    Choose MULTIACTOR only if direct interaction between actors is itself the main subject of the reporting.

    Choose MULTIACTOR when the article is primarily about:
    - negotiations between sides
    - reciprocal threats or responses
    - diplomatic exchanges
    - ceasefire bargaining
    - coordinated or opposing actions between actors
    - direct conflict interaction between multiple parties

    Do NOT choose MULTIACTOR if:
    - the interaction is only context for an explainer
    - the article mainly profiles participants or explains their roles
    - the article mainly explains economic or systemic outcomes
    - the article mainly breaks down issues, constraints, or sticking points

    ---

    NARRATIVE STRICT RULE

    Choose NARRATIVE only when the article mainly reports events in sequence and neither EXPLANATORY nor MULTIACTOR is the dominant function.

    Narrative is a fallback class.
    Do not choose NARRATIVE if the article substantially explains causes, implications, key issues, background, or actor roles.
    Do not choose NARRATIVE if sustained actor-to-actor interaction is the main focus.

    ---

    DECISION RULES (STRICT PRIORITY ORDER)

    1. If the article is primarily argumentative or persuasive → OPINION
    2. Else if the article is primarily explanatory, interpretive, or analytical → EXPLANATORY
    3. Else if the article is primarily about direct interaction between multiple actors → MULTIACTOR
    4. Else → NARRATIVE

    ---

    IMPORTANT CONSTRAINTS

    - Always write the rationale in plain English only.
    - Do not use words or characters from any language other than English.
    - Do NOT classify based on keywords alone.
    - Do NOT rely on the title alone.
    - Focus on the article's overall function.
    - If multiple categories appear, choose the one that dominates the article's purpose.
    - The presence of negotiations, conflict, or multiple actors does NOT automatically make an article MULTIACTOR.
    - If the article explains the meaning, implications, structure, or key issues of those interactions, prefer EXPLANATORY.

    ---

    Return only the structured output."""

    input_text = f"""
    Article title: {article.title}
    Source: {article.source_name}
    Published at: {article.published_at}
    URL: {article.url}

    Content:
    {article.content}

    Deterministic support:
    - opinion: score={support.opinion.score}, reasons={support.opinion.reasons}
    - narrative: score={support.narrative.score}, reasons={support.narrative.reasons}
    - multiactor: score={support.multiactor.score}, reasons={support.multiactor.reasons}
    - explanatory: score={support.explanatory.score}, reasons={support.explanatory.reasons}

    Candidate labels:
    {candidate_labels}

    Task:
    Choose exactly one final label from the candidate labels.

    Before deciding, determine the article's dominant function:
    - explanation / breakdown / implications / profiles / issue structure
    - direct actor interaction / negotiation / confrontation
    - event recounting
    - argument / persuasion

    Then choose the label that best matches that dominant function.

    Give a short rationale grounded in the article's overall purpose, not just its keywords or title.
    """

    response = client.responses.create(
        model="gpt-5.4-mini",
        reasoning={"effort": "medium"},
        instructions=instructions,
        input=input_text,
        text={
            "format": {
                "type": "json_schema",
                "name": "article_classification",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "final_label": {
                            "type": "string",
                            "enum": candidate_labels,
                        },
                        "candidate_labels": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": candidate_labels,
                            },
                            "minItems": len(candidate_labels),
                            "maxItems": len(candidate_labels),
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["final_label", "candidate_labels", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)


def compute_opinion_support(article: NormalizedArticle) -> SupportScore:
    support = SupportScore()

    title = article.title.lower()
    content = article.content.lower()
    text = f"{title} {content}"

    strong_title_markers = [
        "opinion",
        "editorial",
        "commentary",
        "guest essay",
        "column",
    ]

    weak_title_markers = [
        "analysis",
    ]

    first_person_argument_markers = [
        "i think",
        "i believe",
        "in my view",
        "we should",
        "my argument",
        "i would argue",
    ]

    if any(marker in title for marker in strong_title_markers):
        support.add(3, "title_contains_strong_opinion_marker")

    if any(marker in title for marker in weak_title_markers):
        support.add(1, "title_contains_weak_opinion_marker")

    if any(marker in text for marker in first_person_argument_markers):
        support.add(2, "content_contains_first_person_argument")

    return support


def compute_narrative_support(article: NormalizedArticle) -> SupportScore:
    support = SupportScore()

    title = article.title.lower()
    content = article.content.lower()
    text = f"{title} {content}"

    event_verbs = [
        "said",
        "announced",
        "met",
        "agreed",
        "attacked",
        "struck",
        "launched",
        "warned",
        "called",
        "blocked",
        "reported",
        "rejected",
        "steps up",
        "threatens",
    ]

    sequencing_markers = [
        "after",
        "before",
        "then",
        "later",
        "meanwhile",
        "following",
        "as",
        "amid",
    ]

    if any(verb in text for verb in event_verbs):
        support.add(2, "contains_event_action_verbs")

    if any(verb in title for verb in event_verbs):
        support.add(2, "title_contains_event_action")

    if any(marker in text for marker in sequencing_markers):
        support.add(1, "contains_event_sequence_markers")

    return support


def compute_multiactor_support(article: NormalizedArticle) -> SupportScore:
    support = SupportScore()

    title = article.title.lower()
    content = article.content.lower()
    text = f"{title} {content}"

    actors = [
        "iran",
        "israel",
        "united states",
        "us",
        "pakistan",
        "china",
        "russia",
        "lebanon",
        "hezbollah",
        "trump",
        "washington",
        "tehran",
    ]

    interaction_markers = [
        "talks",
        "negotiation",
        "negotiations",
        "ceasefire",
        "responded",
        "response",
        "retaliate",
        "threatened",
        "warned",
        "rejected",
        "met",
        "agreed",
        "blockade",
        "sanctions",
        "refused",
        "accused",
    ]

    explanatory_dampeners = [
        "what to know",
        "all we know",
        "what this means",
        "why it matters",
        "explained",
        "key sticking points",
        "who’s at",
        "who's at",
        "negotiating table",
        "background",
    ]

    actors_found = {actor for actor in actors if actor in text}
    interaction_hits = [marker for marker in interaction_markers if marker in text]

    num_actors = len(actors_found)
    num_interactions = len(interaction_hits)

    if num_actors >= 2 and num_interactions >= 2:
        support.add(3, "direct_actor_interaction_present")

    if num_actors >= 3 and num_interactions >= 3:
        support.add(2, "multi_actor_conflict_or_diplomacy_present")

    if any(
        marker in title
        for marker in ["talks", "ceasefire", "rejects", "warns", "agrees"]
    ):
        support.add(2, "title_signals_direct_actor_interaction")

    # dampen multiactor when article is clearly framed as explanation
    if any(marker in title for marker in explanatory_dampeners):
        support.add(-3, "title_favors_explanatory_over_multiactor")

    return support


def compute_explanatory_support(article: NormalizedArticle) -> SupportScore:
    support = SupportScore()

    title = article.title.lower()
    content = article.content.lower()
    text = f"{title} {content}"

    strong_title_markers = [
        "what to know",
        "all we know",
        "what this means",
        "why it matters",
        "explained",
        "how it works",
        "how it happened",
        "what happened",
        "what are the key",
        "key sticking points",
        "who's at",
        "who's at",
        "negotiating table",
        "background",
    ]

    explanatory_structure_markers = [
        "what happened",
        "what has the us said",
        "how has iran responded",
        "what are the key points",
        "what are the key points of friction",
        "what is achievable",
        "can the divide be bridged",
        "the us delegation",
        "the iranian delegation",
        "what do we know",
        "why it matters",
    ]

    explanatory_content_markers = [
        "because",
        "this means",
        "the implications",
        "the broader context",
        "background",
        "analysts say",
        "in part because",
        "driven by",
        "why it matters",
        "what this means",
        "according to",
        "experts said",
        "experts say",
        "remains unresolved",
        "core issue",
        "sticking points",
        "central dispute",
        "another core issue",
        "the immediate goal",
        "the broader question",
        "best-case scenario",
    ]

    market_impact_markers = [
        "oil prices",
        "markets",
        "equities",
        "investors",
        "brent crude",
        "fuel prices",
        "economic impact",
        "global energy",
    ]

    profile_markers = [
        "born in",
        "served as",
        "is a veteran",
        "is best known as",
        "delegation",
        "negotiator",
        "foreign minister",
        "vice president",
        "special envoy",
    ]

    if "?" in title:
        support.add(2, "title_contains_question")

    if any(marker in title for marker in strong_title_markers):
        support.add(5, "title_contains_strong_explanatory_marker")

    structure_hits = sum(
        1 for marker in explanatory_structure_markers if marker in text
    )
    if structure_hits >= 2:
        support.add(4, "article_has_explanatory_structure")
    elif structure_hits == 1:
        support.add(2, "article_has_partial_explanatory_structure")

    content_hits = sum(1 for marker in explanatory_content_markers if marker in text)
    if content_hits >= 3:
        support.add(4, "content_contains_multiple_explanatory_markers")
    elif content_hits >= 1:
        support.add(2, "content_contains_explanatory_marker")

    if any(marker in text for marker in market_impact_markers):
        support.add(4, "article_explains_market_or_systemic_effects")

    if any(marker in text for marker in profile_markers):
        support.add(1, "article_explains_actor_background_or_roles")

    return support


def compute_rule_support(article: NormalizedArticle) -> RuleSupport:
    return RuleSupport(
        opinion=compute_opinion_support(article),
        narrative=compute_narrative_support(article),
        multiactor=compute_multiactor_support(article),
        explanatory=compute_explanatory_support(article),
    )


def top_two_labels(rule_support: RuleSupport) -> list[tuple[str, int]]:
    ranked = [
        ("multiactor", rule_support.multiactor.score),
        ("explanatory", rule_support.explanatory.score),
    ]
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked


def classify_single_article(
    article: NormalizedArticle,
    support: RuleSupport,
    top_two: list[tuple[str, int]],
) -> ClassificationResult:

    llm_result = call_classification_llm(article, support, top_two)

    assert article.id is not None

    return ClassificationResult(
        normalized_article_id=article.id,
        source_name=article.source_name,
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        content=article.content,
        has_full_content=article.has_full_content,
        original_snippet=article.original_snippet,
        opinion_score=support.opinion.score,
        narrative_score=support.narrative.score,
        multiactor_score=support.multiactor.score,
        explanatory_score=support.explanatory.score,
        opinion_reasons=support.opinion.reasons,
        narrative_reasons=support.narrative.reasons,
        multiactor_reasons=support.multiactor.reasons,
        explanatory_reasons=support.explanatory.reasons,
        top_two=top_two,
        final_label=llm_result["final_label"],
        rationale=llm_result["rationale"],
        llm_label=llm_result["final_label"],
        was_llm_used=True,
    )


def classify_articles(
    normalized_articles: list[NormalizedArticle],
) -> list[ClassificationResult]:
    results = []

    for article in normalized_articles:
        support = compute_rule_support(article)
        top_two = top_two_labels(support)
        result = classify_single_article(article, support, top_two)
        results.append(result)

    return results


if __name__ == "__main__":
    from db import (
        load_normalized_articles_for_classification,
        insert_classification_results,
    )

    normalized_articles = load_normalized_articles_for_classification()
    classification_results = []

    print(f"Loaded {len(normalized_articles)} normalized articles from DB.")

    for article in normalized_articles:
        print("----")
        print("ID:", article.id)
        print("TITLE:", article.title)
        print("URL:", article.url)
        print("has_full_content:", article.has_full_content)
        print("original_snippet:", article.original_snippet[:300])

        support = compute_rule_support(article)
        top_two = top_two_labels(support)

        result = classify_single_article(article, support, top_two)
        classification_results.append(result)

        print("OPINION:", support.opinion.score, support.opinion.reasons)
        print("NARRATIVE:", support.narrative.score, support.narrative.reasons)
        print("MULTIACTOR:", support.multiactor.score, support.multiactor.reasons)
        print("EXPLANATORY:", support.explanatory.score, support.explanatory.reasons)
        print("TOP TWO:", top_two)
        print("FINAL LABEL:", result.final_label)
        print("RATIONALE:", result.rationale)

    insert_classification_results(classification_results)
    print(f"Inserted {len(classification_results)} classification results.")
