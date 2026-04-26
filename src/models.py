from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional


@dataclass
class RawArticle:
    source_name: Optional[str]
    author: Optional[str]
    title: Optional[str]
    description: Optional[str]
    url: Optional[str]
    url_to_image: Optional[str]
    published_at: Optional[datetime]
    content: Optional[str]

    retrieved_at: datetime
    query: str


@dataclass
class NormalizedArticle:
    source_name: str
    title: str
    url: str
    published_at: str

    content: str  # final text used downstream
    original_snippet: str  # NewsAPI snippet/preview
    has_full_content: bool  # whether content is real extracted article text

    is_valid: bool
    invalid_reasons: list[str]
    id: Optional[int] = None


@dataclass
class SupportScore:
    score: int = 0
    reasons: list[str] = field(default_factory=list)

    def add(self, weight: int, reason: str) -> None:
        self.score += weight
        self.reasons.append(reason)


@dataclass
class RuleSupport:
    opinion: SupportScore
    narrative: SupportScore
    multiactor: SupportScore
    explanatory: SupportScore


@dataclass
class ClassificationResult:
    normalized_article_id: int
    source_name: str
    title: str
    url: str
    published_at: str
    content: str
    has_full_content: bool
    original_snippet: str

    opinion_score: int
    narrative_score: int
    multiactor_score: int
    explanatory_score: int

    opinion_reasons: List[str]
    narrative_reasons: List[str]
    multiactor_reasons: List[str]
    explanatory_reasons: List[str]

    top_two: List[Tuple[str, int]]

    final_label: str
    rationale: str

    llm_label: Optional[str] = None
    was_llm_used: bool = True
    id: Optional[int] = None
    created_at: str = ""


@dataclass
class Batch:
    id: Optional[int] = None
    run_id: Optional[str] = None
    batch_type: str = ""
    articles: List[ClassificationResult] = field(default_factory=list)


@dataclass
class BatchAnalysis:
    id: Optional[int] = None
    batch_id: int = 0

    batch_type: str = ""
    article_count: int = 0
    article_titles: list[str] = field(default_factory=list)

    summary: str = ""
    full_analysis: Dict[str, Any] = field(default_factory=dict)

    is_valid: bool = False
    failure_reason: Optional[str] = None


@dataclass
class EventSummary:
    batch_analysis_id: int
    batch_type: str
    headline: str
    deck: str
    website_summary: str
    key_points: list[str]
    source_titles: list[str]
    is_valid: bool
    failure_reason: Optional[str] = None
    raw_output: Optional[str] = None
    source_links: list[SourceLink] = field(default_factory=list)


@dataclass
class SourceLink:
    title: str
    source: str
    url: str
    published_at: str
