# architecture.md

## System Overview

This system is a staged news-analysis pipeline that combines deterministic validation and rule enforcement with constrained LLM assistance.

The pipeline begins by retrieving raw article records from NewsAPI. Those records are then normalized into a strict internal article schema so that downstream stages operate on consistent data. Only normalization-valid articles continue to classification. Classification assigns exactly one final article type per article using deterministic rule checks together with LLM support, while preserving the rule constraints defined in Dafny. Classified non-rejected articles are then grouped into compatible batches. Each formed batch is analyzed with an LLM to produce structured analysis results and user-facing summaries.

The system is split into stages to preserve clear boundaries between external ingestion, deterministic validation, per-article reasoning, collection-level grouping, and batch-level analysis. This separation keeps the implementation consistent with the TLA+ system model, makes local rules easier to test in isolation, and prevents responsibilities from collapsing into one opaque pipeline.

## Design Goals

- deterministic-first execution  
  Deterministic checks and transformations are the primary decision mechanism wherever rules exist. LLM outputs may support classification and analysis, but they must not replace required rule enforcement.

- LLM assistance only where allowed  
  LLM calls are limited to the stages that explicitly require them: article classification support and batch analysis. LLM outputs must remain bounded by the repository’s prompt and schema definitions.

- strict stage separation  
  Each module owns one stage or one bounded support concern. External API access, normalization, classification, batching, and batch analysis must remain separated so that each stage has a clear input, output, and failure surface.

- consistency with TLA+ and Dafny  
  The architecture must preserve the global stage ordering and invariants defined by TLA+, while applying Dafny-defined local correctness rules across collections of articles and batches.

- testable stage-local logic  
  Rule evaluation, normalization checks, compatibility decisions, and output parsing should be implemented in stage-local or shared deterministic helpers that can be tested independently from external APIs and LLM calls.

## End-to-End Pipeline Flow

`ingest -> normalize -> classify -> assign_batches -> analyze_batches -> output_generation`

1. **ingest**  
   Fetch raw article data from NewsAPI and convert responses into `RawArticle` objects.

2. **normalize**  
   Clean, canonicalize, and validate raw records into `NormalizedArticle` objects, with explicit validity and usability outcomes.

3. **classify**  
   Apply deterministic classification support checks and LLM-assisted classification to produce one `ClassificationResult` per normalization-valid article.

4. **assign_batches**  
   Group classified, non-rejected articles into compatible `Batch` objects according to batch type and capacity rules.

5. **analyze_batches**  
   Convert each valid formed batch into batch-analysis prompt input, invoke the batch-analysis LLM flow, and parse the result into `BatchAnalysis`.

6. **output_generation**  
   Convert completed batch analyses into structured internal outputs and user-facing summaries or reports.

The output of each stage becomes the input of the next stage. Invalid or rejected items must not bypass stage gates and proceed downstream.

## Module Layout

### ingest_news.py

#### Ingestion Interface Decisions
- The Python pipeline uses synchronous stage functions.
- Shared typed models live in `src/models.py`.
- Shared configuration objects and constants live in `src/config.py`.
- `ingest_news.py` exposes a synchronous ingestion entry point consumed by `pipeline.py`.
- NewsAPI access should use explicit HTTP requests rather than a third-party wrapper unless explicitly instructed otherwise.
- Ingestion performs bounded retries and pagination, and converts API responses into `RawArticle` objects.
- Ingestion does not perform downstream normalization or semantic deduplication.

**Purpose**  
Implements the ingestion stage only. It is responsible for retrieving article data from NewsAPI and translating external API responses into the pipeline’s raw internal representation.

**Inputs**  
- ingestion configuration such as query parameters, page size, endpoint choice, and date/range filters
- API credentials or client configuration
- retry and pagination settings

**Outputs**  
- a collection of `RawArticle` objects
- optional ingestion metadata such as source endpoint, page information, retrieval timestamp, or request diagnostics

**Dependencies**  
- NewsAPI request/response rules from `API_documentation/`
- shared typed models for `RawArticle`
- shared HTTP/client or retry utilities if introduced under `src/`

**Notes**  
This module must not perform normalization, classification, batching, or analysis. Its job ends once external responses are converted into stage-appropriate raw objects.

### normalize_articles.py

**Purpose**  
Implements the normalization stage only. It transforms external raw article records into validated internal article objects with canonical field values and explicit validity outcomes.

**Inputs**  
- a collection of `RawArticle` objects from ingestion

**Outputs**  
- a collection of `NormalizedArticle` objects
- normalization validity flags and reasons for failure or unusable records

**Dependencies**  
- normalization rules defined by Dafny
- shared typed models for `NormalizedArticle`
- shared helpers for field cleanup, URL/timestamp normalization, and validation

**Notes**  
This module is the boundary between external, inconsistent source data and the pipeline’s strict internal schema. It must not fetch data or assign article types. It should make downstream eligibility explicit.

### classify_articles.py

**Purpose**  
Implements per-article classification only. It determines one final article type for each normalization-valid article, using deterministic rule support and LLM assistance where allowed.

**Inputs**  
- normalization-valid `NormalizedArticle` objects

**Outputs**  
- one `ClassificationResult` per processed article
- final article type assignment for each article
- supporting evidence, rule-check results, or structured classification metadata as needed

**Dependencies**  
- classification rules defined by Dafny
- classification prompts and schemas from `LLM Prompts and Schemas/`
- shared LLM client and structured parser helpers
- shared typed models for `ClassificationResult`

**Notes**  
This module must treat deterministic constraints as authoritative. LLM output may inform classification, but it cannot override rule constraints. Rejected or unsupported articles must be explicitly marked and not silently passed downstream.

### assign_batches.py

**Purpose**  
Implements collection-level batch assignment only. It groups classified non-rejected articles into compatible batches based on article type and batching rules.

**Inputs**  
- a collection of `ClassificationResult` objects, or classified article records carrying final article type

**Outputs**  
- a collection of `Batch` objects with explicit batch type and membership
- batch state information, including incomplete or leftover cases where relevant

**Dependencies**  
- batch assignment rules defined by Dafny
- shared typed models for `Batch`
- shared helpers for compatibility checks, ordering policy, and capacity enforcement

**Notes**  
This module operates at the collection level rather than the individual article level, but it must apply the local compatibility rules consistently across all articles. It must not reclassify articles or perform analysis.

### analyze_batches.py

**Purpose**  
Implements batch-level analysis only. It converts formed batches into batch-analysis prompts, executes the batch-analysis LLM flow, and parses structured results into internal analysis objects.

**Inputs**  
- valid `Batch` objects produced by batch assignment

**Outputs**  
- a collection of `BatchAnalysis` objects
- detailed analysis and compact user-facing summary content for each batch
- structured failure information for malformed or unsuccessful analyses

**Dependencies**  
- batch-analysis prompts and schemas from `LLM Prompts and Schemas/`
- shared LLM client and output parser helpers
- shared typed models for `BatchAnalysis`

**Notes**  
This module should preserve the required article ordering inside prompts and treat schema validation seriously. It must not change batch membership, reinterpret article types, or absorb output orchestration responsibilities beyond producing batch-analysis results.

### pipeline.py

**Purpose**  
Implements orchestration only. It coordinates stage execution in the required order and ensures that outputs are passed downstream without collapsing stage boundaries.

**How orchestration works**  
- starts the pipeline run
- calls ingestion to obtain raw articles
- passes raw articles to normalization
- filters or gates invalid normalization outputs from downstream progression
- passes normalization-valid articles to classification
- excludes rejected articles from batching
- passes compatible classified articles to batch assignment
- passes formed valid batches to batch analysis
- collects batch-analysis results and hands them to output generation or emission logic
- applies logging, checkpointing, resumability, and explicit error propagation rules at stage boundaries

**Dependencies**  
- all stage modules under `src/`
- shared logging/configuration utilities
- shared models used to transfer state between stages

**Notes**  
`pipeline.py` is the execution coordinator, not the home for detailed stage logic. It should make the order of operations, stage boundaries, and failure propagation explicit, while leaving local business rules inside the stage modules that own them.

## Shared Models

The pipeline uses stage-specific structured models to keep responsibilities explicit and to prevent raw external data from leaking across stage boundaries.

These models may be implemented as dataclasses, Pydantic models, TypedDicts, or similarly explicit typed structures.  
JSON may be used at external boundaries, but internal pipeline stages should operate on structured stage-appropriate objects.

### RawArticle
Represents the ingestion-level article record immediately after NewsAPI response parsing.

Purpose:
- preserve the external article payload in a controlled internal form
- capture only the fields needed by downstream normalization
- attach ingestion metadata when useful

Typical contents:
- source name or source object
- author
- title
- description
- URL
- published timestamp
- content/text fields returned by NewsAPI
- ingestion metadata such as retrieval time, endpoint, or page number

Notes:
- `RawArticle` is the closest internal representation to NewsAPI JSON
- it is not yet trusted for downstream reasoning
- it may contain missing, inconsistent, or low-quality fields

### NormalizedArticle
Represents a validated and canonicalized article after normalization.

Purpose:
- provide a strict internal schema for downstream stages
- expose cleaned and normalized article fields
- make usability and validity explicit

Typical contents:
- canonical title
- canonical source name
- canonical URL
- normalized timestamp
- normalized text/content fields
- validation or usability flags
- failure reasons or normalization notes when relevant

Notes:
- only normalization-valid articles should proceed to classification
- this is the main article object used for deterministic rule checks and classification

### ClassificationResult
Represents the result of per-article classification.

Purpose:
- record the final article type
- preserve deterministic rule support and LLM-derived support
- expose the classification decision in a structured form

Typical contents:
- reference to the article being classified
- final article type:
  - opinion
  - narrative
  - multiactor
  - explanatory
  - reject
- deterministic support or rule-check results
- optional LLM output summary or parsed classification fields
- classification evidence or rationale metadata
- rejection reason if classified as `reject`

Notes:
- each normalization-valid article must produce exactly one final classification result
- LLM-derived signals do not replace deterministic constraints

### Batch
Represents a collection of classified articles grouped for batch-level analysis.

Purpose:
- hold only classification-compatible articles
- preserve batch type and membership state
- provide the unit of downstream batch analysis

Typical contents:
- batch type:
  - Empty
  - BatchOpinion
  - BatchNarrative
  - BatchMultiactor
  - BatchExplanatory
- ordered collection of member articles or classification results
- batch size / capacity state
- formation status or completeness metadata if needed

Notes:
- a batch must not mix incompatible article types
- rejected articles must never appear in a batch

### BatchAnalysis
Represents the structured result of analyzing a formed batch.

Purpose:
- capture the machine-readable output of batch-level reasoning
- preserve summarized and detailed analysis derived from the batch
- provide the main input to final output generation

Typical contents:
- reference to the analyzed batch
- parsed structured LLM output
- summary text
- detailed analysis text
- confidence, status, or fallback metadata
- analysis failure information when applicable

Notes:
- `BatchAnalysis` is the internal representation of batch-analysis results
- it may later be serialized to JSON for output, but internally it should remain structured

### UserOutput
Represents the final output emitted by the pipeline for downstream consumption or user display.

Purpose:
- package completed analysis results into the final output format
- separate internal analysis representation from final presentation

Typical contents:
- user-facing summary
- detailed report sections
- structured output payloads derived from batch analyses
- metadata about included batches, skipped batches, or failure cases

Notes:
- `UserOutput` is the final stage object
- it may be serialized to JSON, returned as structured Python objects, or formatted for display depending on the final execution environment

## Data Flow Between Stages

Each stage accepts a defined input object type, produces a defined output object type, and applies explicit filtering and failure behavior before downstream execution continues.

### ingestion
**Input object type**
- ingestion configuration and external API request parameters

**Output object type**
- collection of `RawArticle`

**Filtering rules**
- no semantic filtering beyond bounded API/result handling
- raw records are collected as returned, then shaped into `RawArticle`

**Failure behavior**
- API failures, pagination failures, or parse failures are surfaced explicitly
- ingestion may fail the run or return partial raw results depending on orchestration policy
- ingestion does not guess missing response fields beyond safe parsing defaults

### normalization
**Input object type**
- collection of `RawArticle`

**Output object type**
- collection of `NormalizedArticle`

**Filtering rules**
- invalid, incomplete, or unusable raw articles are marked accordingly during normalization
- only normalization-valid articles may proceed to classification

**Failure behavior**
- expected data-quality failures are represented as invalid normalization outcomes, not crashes
- malformed records should preserve failure reasons where possible
- systemic normalization errors should be surfaced to orchestration explicitly

### classification
**Input object type**
- collection of normalization-valid `NormalizedArticle`

**Output object type**
- collection of `ClassificationResult`

**Filtering rules**
- only normalization-valid articles are classified
- each processed article must receive exactly one final classification result
- articles classified as `reject` are filtered out from downstream batch assignment

**Failure behavior**
- malformed or incomplete LLM outputs must trigger explicit fallback or failure handling
- deterministic rule failure takes precedence over unsupported LLM classification
- the stage must not fabricate a supported classification when evidence is insufficient

### batch_assignment
**Input object type**
- collection of non-rejected `ClassificationResult`

**Output object type**
- collection of `Batch`

**Filtering rules**
- only classification-compatible articles may be grouped into the same batch
- rejected articles are excluded
- incomplete or leftover batch cases are handled according to batching rules

**Failure behavior**
- incompatible articles must not be forced into a batch
- batch formation issues should remain explicit in batch state or orchestration-visible results
- the stage must not reinterpret article types to make batching succeed

### batch_analysis
**Input object type**
- collection of valid formed `Batch`

**Output object type**
- collection of `BatchAnalysis`

**Filtering rules**
- only valid formed batches are analyzed
- empty or invalid batches should not be sent to the LLM analysis stage

**Failure behavior**
- malformed LLM outputs, parse failures, or analysis-call failures must be represented explicitly
- failed analysis must not be converted into fabricated successful output
- fallback behavior should remain bounded and schema-consistent

### output_generation
**Input object type**
- collection of `BatchAnalysis`

**Output object type**
- `UserOutput` or collection of `UserOutput`, depending on orchestration design

**Filtering rules**
- only successful or explicitly handled analysis results should be included in final user-facing output
- failed analyses may be omitted or represented explicitly, but not silently treated as successful

**Failure behavior**
- output formatting failures should be surfaced explicitly
- output generation must not mutate prior stage decisions
- final output should reflect available successful analyses without inventing missing content

## LLM Integration Design
- classification LLM location
- batch analysis LLM location
- prompt loading
- schema parsing
- fallback handling
- why raw API calls are isolated

## Error Handling Strategy
- expected data failures
- expected API failures
- expected schema/LLM failures
- propagation vs local handling

## Logging / Checkpointing Strategy
- what gets logged
- where stage-level counts are captured
- resumability hooks if needed

## Extension Constraints
How future additions must preserve:
- stage order
- domain concepts
- typed boundaries
- no new invented stages/types without instruction