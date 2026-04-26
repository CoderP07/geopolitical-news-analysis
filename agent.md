# agent.md

## Project Purpose
This system implements a deterministic + LLM-assisted news analysis pipeline:

1. Ingestion  
  Fetch recent articles from NewsAPI and convert them into a standardized raw format.
  Unless explicitly instructed otherwise, Codex should assume:
  - synchronous Python stage interfaces
  - shared typed models in `src/models.py`
  - shared config/constants in `src/config.py`
  - explicit HTTP requests for NewsAPI access
  - bounded retry handling for 429 and transient failures
  - no semantic deduplication during ingestion beyond narrow exact-duplicate suppression if implemented
  - explicit preservation of ingestion metadata needed for traceability

2. Normalization  
  Validate and normalize all articles into a strict internal schema.  
  Only articles that pass normalization are allowed to proceed.

3. Classification (Per-Article)  
   Each normalized article is assigned exactly one type:
   - opinion
   - narrative
   - multiactor
   - explanatory
   - reject

   Classification is determined by:
   - deterministic rule checks (required)
   - LLM signals (supporting)

   Final classification must satisfy rule constraints defined in Dafny.

4. Batch Assignment (Collection-Level)  
   Classified articles are grouped into batches based on type compatibility:
   - BatchOpinion
   - BatchNarrative
   - BatchMultiactor
   - BatchExplanatory
   - Empty

   Batches may only contain articles of a compatible type.

5. Batch Analysis  
   Each batch is analyzed using an LLM to produce:
   - structured analysis output
   - summarized report for user consumption

The pipeline must strictly follow the ordering and invariants defined in TLA+ and apply all Dafny rule constraints during execution.
## Source of Truth / Precedence
When conflicts or ambiguities appear, follow this precedence:

1. TLA+ (test.tla)
   - Defines the global system behavior, pipeline stages, and invariants.
   - Specifies allowed state transitions and ordering between stages.
   - This is the authoritative definition of how the overall system must behave.

2. Dafny Procedures (normalization.dfy, classification.dfy, batch_assignment.dfy)
   - Define per-article and per-operation correctness rules.
   - These represent local logic that must be applied consistently across all articles and batches.
   - Dafny procedures must NOT be altered by Codex unless explicitly instructed.

3. Python Implementation (src/)
   - Codex must implement the pipeline by:
     - Orchestrating stages in the order defined by TLA+
     - Applying Dafny-defined logic across collections of articles
     - Preserving all invariants defined in TLA+

Codex must treat:
- TLA+ as the global orchestration model
- Dafny as the local rule system
- Python as the execution layer that connects both

## Repository Navigation
- src/
  Contains all Python implementation code for the pipeline.
  This is where Codex will build and modify the system.
  Includes:
    - ingestion logic (NewsAPI client + ingestion orchestration)
    - normalization logic
    - classification pipeline
    - batch assignment logic
    - batch analysis logic
    - pipeline orchestration
    - shared models and utility functions

- Data Pipeline/
  Contains formal system modeling and state design using TLA+ / PlusCal.
  This defines:
    - pipeline stages
    - state transitions
    - global invariants
    - allowed system behavior
  Codex must treat this as read-only unless explicitly instructed.

- Data Pipeline/DafnyProcedureEnforcement/
  Contains Dafny procedures that define per-article and per-operation correctness rules.
  These include:
    - normalization rules
    - classification constraints
    - batch assignment constraints
  Codex must implement logic consistent with these rules, but must NOT modify these files.

- LLM Prompts and Schemas/
  Contains all prompt templates and structured output schemas used for LLM calls.
  This includes:
    - article classification prompts
    - batch analysis prompts
    - output formatting schemas
  Codex should use these when implementing LLM calls and must not invent new output formats without instruction.

- API_documentation/
  Contains external API specifications and execution rules.
  This includes:
    - NewsAPI documentation
    - NewsAPI execution constraints (pagination, filtering, error handling)
    - OpenAI API usage guidance
  Codex must follow these rules when implementing API interactions.

- agent.md
  Defines how Codex should behave in this repository.
  Includes:
    - project purpose
    - source of truth / precedence
    - implementation rules
    - module responsibilities
    - constraints and boundaries

- architecture.md
  Defines the system design and pipeline structure.
  Includes:
    - stage breakdown
    - data flow between modules
    - separation of concerns
    - high-level implementation plan

## Allowed Domain Concepts

Codex must use only the following domain concepts unless explicitly instructed otherwise.

### Article Types
Each article may be assigned exactly one final article type:
- unassigned
- opinion
- narrative
- multiactor
- explanatory
- reject

Definitions:
- unassigned: article has not yet received a final classification
- opinion: article is classified as opinion
- narrative: article is classified as narrative
- multiactor: article is classified as involving multiple relevant actors
- explanatory: article is classified as explanatory
- reject: article is not suitable for downstream analysis

Codex must not invent new article types or synonyms.

### Batch Types
Each batch may have exactly one batch type:
- Empty
- BatchOpinion
- BatchNarrative
- BatchMultiactor
- BatchExplanatory

Definitions:
- Empty: batch has not yet been assigned a valid article type
- BatchOpinion: contains only compatible opinion articles
- BatchNarrative: contains only compatible narrative articles
- BatchMultiactor: contains only compatible multiactor articles
- BatchExplanatory: contains only compatible explanatory articles

Codex must not invent new batch types or mix incompatible article types within a batch.

### Pipeline Stages
The pipeline consists only of the following ordered stages:
1. ingestion
2. normalization
3. classification
4. batch_assignment
5. batch_analysis
6. output_generation

Definitions:
- ingestion: fetch articles from external source(s)
- normalization: validate and convert articles into internal structured form
- classification: assign one article type per normalized article using deterministic rules and LLM support
- batch_assignment: group classified articles into compatible batches
- batch_analysis: run LLM analysis over formed batches
- output_generation: produce structured and user-facing outputs from analysis results

Codex must not reorder, skip, merge, or invent new pipeline stages unless explicitly instructed.

### Allowed Data Objects / Schemas
Codex may implement structured data models for the following concepts:
- RawArticle
- NormalizedArticle
- ClassificationResult
- Batch
- BatchAnalysis
- UserOutput

Suggested intent:
- RawArticle: direct ingestion-level representation from NewsAPI
- NormalizedArticle: validated internal article representation
- ClassificationResult: article type plus supporting evidence / metadata
- Batch: collection of compatible classified articles
- BatchAnalysis: structured result of analyzing a batch
- UserOutput: final summarized and detailed output returned to the user

Codex must keep these objects structured and stage-specific.
Codex must not collapse the entire pipeline into one generic object.

### Allowed Decision Logic
The following decision pattern is allowed:
- deterministic validation for normalization
- deterministic rule support for classification
- LLM-assisted classification subject to rule constraints
- deterministic batch compatibility checks
- LLM-assisted batch analysis
- structured output generation

The following are not allowed unless explicitly instructed:
- pure LLM-only classification without rule constraints
- batch creation before classification
- downstream analysis of rejected or invalid articles
- invention of new actor types, article types, batch types, or stage names

### Prompt and Schema Usage
Codex may use only the prompts and schemas present in:
- LLM Prompts and Schemas/

Codex must not invent new prompt families or output schema families unless explicitly instructed.

## Implementation Boundaries

Codex may modify only files under `src/` in order to implement the required procedures.

Codex must not modify files in:
- `Data Pipeline/`
- `API_documentation/`
- `LLM Prompts and Schemas/`
- `agent.md`
- `architecture.md`

These files and directories are read-only and must be treated as ground truth.
Codex must implement behavior in `src/` so that it remains consistent with those sources.
Codex must not create new top-level directories unless explicitly instructed.

## Required Module Responsibilities

Each Python module in `src/` must own exactly one stage of the pipeline or one clearly bounded support concern.  
Modules must not absorb responsibilities that belong to other stages.

### ingest_news.py
Owns ingestion only. Responsibilities:
- call NewsAPI and fetch raw article records
- select endpoints and apply request parameters
- handle pagination and bounded retries
- parse API responses into the pipeline’s `RawArticle` representation
- preserve ingestion metadata needed for downstream tracing

Must not:
- normalize article fields
- classify articles
- assign batches
- analyze batches

### normalize_articles.py
Owns normalization only. Responsibilities:
- transform `RawArticle` into `NormalizedArticle`
- clean and canonicalize fields
- normalize timestamps, URLs, source names, and text fields
- compute validation and usability flags
- determine whether an article is valid for downstream processing
- preserve reasons for invalidity or rejection-at-normalization

Must not:
- fetch from external APIs
- classify article type
- assign articles to batches
- run LLM batch analysis

### classify_articles.py
Owns per-article classification only. Responsibilities:
- accept only normalized, normalization-valid articles
- run deterministic eligibility and support checks required by Dafny
- invoke the classification LLM when needed
- reconcile LLM outputs with deterministic rule constraints
- assign exactly one final article type per article
- produce a `ClassificationResult` with evidence, rule support, and final label
- mark unsupported articles as `reject` when required

Must not:
- mutate normalized article contents except for attaching classification outputs
- group articles into batches
- perform batch-level reasoning
- generate final user reports

### assign_batches.py
Owns collection-level batch formation only. Responsibilities:
- consume classified articles that are not rejected
- derive batch compatibility from final article type
- create batches and append compatible articles
- enforce capacity, size, and ordering rules
- preserve batch state and batch type consistency
- handle partial, leftover, or incomplete batches according to project rules
- output structured `Batch` objects only

Must not:
- reclassify articles
- reinterpret article type semantics
- run LLM analysis
- generate user-facing summaries

### analyze_batches.py
Owns batch-level analysis only. Responsibilities:
- accept valid formed batches
- transform each batch into the required batch-analysis prompt input
- preserve article ordering policy inside prompts
- call the LLM for batch analysis
- parse structured batch-analysis outputs
- produce `BatchAnalysis` objects
- generate both detailed analysis and compact summaries
- handle confidence failures, malformed outputs, and fallback behavior

Must not:
- fetch articles
- normalize articles
- classify individual articles
- create or modify batch membership rules

### pipeline.py
Owns orchestration only. Responsibilities:
- execute the pipeline strictly in this order:
  `ingest -> normalize -> classify -> assign_batches -> analyze_batches -> emit_outputs`
- pass outputs from one stage to the next without changing stage semantics
- enforce stage sequencing and stop invalid downstream execution
- provide logging, checkpointing, resumability, and error propagation hooks
- coordinate output generation from completed batch analyses

Must not:
- contain the detailed business logic of normalization, classification, batching, or analysis
- duplicate rules that belong inside stage modules

### Shared support code
If helper modules are introduced under `src/`, they may only contain reusable support logic such as:
- typed data models
- enum definitions for allowed article types, batch types, and stage names
- shared validation helpers
- LLM client wrappers
- schema parsers
- logging/utilities

Shared support code must not become an alternative execution path for the pipeline and must not blur ownership between stages.

## Coding Rules

The Python implementation must follow these coding rules.

### General Structure
- Prefer small, single-purpose functions.
- Prefer explicit stage boundaries over clever abstractions.
- Keep orchestration separate from business logic.
- Do not collapse multiple pipeline stages into one function or one file.
- Avoid deep nesting when a guard clause or helper function is clearer.

### Typing and Data Models
- Use typed models for all stage outputs and shared pipeline objects.
- Represent core concepts with explicit structured types, not loose dictionaries where avoidable.
- At minimum, keep typed representations for:
  - `RawArticle`
  - `NormalizedArticle`
  - `ClassificationResult`
  - `Batch`
  - `BatchAnalysis`
  - `UserOutput`
- Use enums or fixed constants for article types, batch types, and pipeline stages.
- Do not use ad hoc string values scattered across the codebase for domain concepts.

### Function Design
- Each function should have one clear responsibility.
- Prefer pure functions for validation, normalization, derivation, and compatibility checks.
- Functions should return structured results rather than overloaded tuples when the meaning is not obvious.
- Keep side effects localized and visible.
- Avoid functions that both compute decisions and perform I/O unless that is the module’s explicit responsibility.

### Duplication and Reuse
- Do not duplicate normalization, classification, or compatibility logic across modules.
- Shared logic must be extracted into support helpers or shared model/util modules under `src/`.
- The same rule must have one authoritative implementation in Python.
- Avoid copy-pasted prompt-building, parsing, or validation code.

### LLM Integration
- All LLM API interaction must be isolated behind a small client wrapper or dedicated helper layer.
- Prompt construction must be separated from response parsing.
- Structured output parsing must be explicit and validated.
- LLM results must never bypass deterministic rule checks.
- Retries, fallback behavior, and malformed-output handling must be centralized rather than reimplemented per call site.
- Do not scatter raw API calls throughout the pipeline modules.

### Error Handling
- Failures must be explicit.
- Do not silently swallow exceptions.
- Stage modules should return structured failure information when appropriate.
- Pipeline orchestration should decide whether to stop, skip, retry, or propagate an error.
- Validation failures are data outcomes, not crashes, when they are expected by design.

### Logging and Observability
- Add lightweight logging at stage boundaries and important decision points.
- Log counts and transitions, not excessive noisy internals.
- Preserve enough metadata to trace why an article was rejected, classified a certain way, or placed into a batch.
- Logging must not change pipeline behavior.

### Testing and Determinism
- Prefer deterministic helpers that are easy to unit test.
- Put rule evaluation in testable functions independent from network or LLM calls.
- Keep non-deterministic behavior isolated to explicit external-call boundaries.
- Do not embed hidden randomness in classification, batching, or output generation.

### State and Mutation
- Do not mutate shared objects unpredictably across stages.
- Prefer creating the next stage’s object explicitly from the previous stage’s output.
- If mutation is used for performance or clarity, keep it local and controlled.
- Batch state transitions must remain explicit and consistent with TLA+ invariants.

### Configuration and Constants
- Keep configurable limits, thresholds, and retry settings centralized.
- Do not hardcode the same constant in multiple places.
- Prompt names, model names, batch size limits, and retry counts should come from clearly defined configuration points.

### Readability
- Use descriptive names that match domain concepts from `agent.md`.
- Do not invent synonyms for article types, batch types, or stages.
- Prefer straightforward control flow over abstraction-heavy designs.
- Comments should explain constraints, invariants, or non-obvious decisions, not restate obvious code.

### Boundaries
- `pipeline.py` may orchestrate stages, but must not absorb detailed per-stage logic.
- Stage modules may implement their own rules, but must not reach forward and perform downstream stage responsibilities.
- Shared helper modules may support multiple stages, but must not become an unstructured dumping ground.

## Ambiguity Handling

When information is missing, incomplete, or ambiguous, Codex must resolve it conservatively and in a way that preserves the formal model.

### Source-of-Truth Resolution
- First consult the declared precedence order in this repository:
  1. TLA+ for global stage ordering, state transitions, and invariants
  2. Dafny for local rule correctness
  3. Existing Python module boundaries and prompt/schema files
- If a lower-precedence source conflicts with a higher-precedence source, follow the higher-precedence source.

### When Behavior Is Underspecified
- Prefer the smallest implementation decision that preserves existing stage boundaries and invariants.
- Do not invent new pipeline stages, article types, batch types, schemas, or prompt families.
- Do not rename domain concepts or introduce synonyms.
- Do not broaden module responsibilities just to “make the code easier.”

### When a Rule Is Missing in Python
- Implement the Python logic in the narrowest way that matches the intent of the corresponding TLA+ or Dafny definition.
- Keep the implementation local to the correct stage module.
- Add a brief comment marking the assumption when the mapping is not fully explicit.

### When LLM Behavior Is Unclear
- Prefer deterministic validation and constraint enforcement over trusting the LLM.
- Treat LLM output as supporting evidence, not authoritative truth, unless the repository explicitly says otherwise.
- If structured output is malformed or incomplete, use the defined fallback path rather than guessing missing fields.

### When Data Is Missing or Low Quality
- Prefer rejection, invalidation, or explicit unusable-state marking over guessing missing article fields.
- Do not fabricate article content, source metadata, timestamps, actor information, or classification evidence.
- Preserve the reason an article could not proceed.

### When Multiple Reasonable Implementations Exist
- Choose the option that:
  1. preserves TLA+ ordering and invariants,
  2. respects Dafny constraints,
  3. keeps responsibilities separated by module,
  4. is easiest to test and reason about.
- Prefer explicit, simple implementations over clever abstractions.

### When Existing Files Are Silent
- Reuse existing repository patterns if they do not conflict with the formal model.
- If no pattern exists, implement the minimal clean solution inside `src/` only.
- Do not create new top-level directories or frameworks unless explicitly instructed.

### Assumption Handling
- Local assumptions must be:
  - minimal
  - documented with a short comment near the relevant code
  - non-expansive with respect to domain concepts
- Assumptions must not contradict TLA+, Dafny, prompt schemas, or declared module responsibilities.

### Failure Preference
- When forced to choose between:
  - guessing and continuing, or
  - failing conservatively with explicit reasoning,
  prefer conservative failure.
- It is better to mark an article as invalid/reject, or a batch analysis as failed, than to fabricate unsupported downstream state.

### Escalation Rule
- If ambiguity would require changing:
  - formal invariants,
  - allowed domain concepts,
  - stage ordering,
  - schema families,
  - or repository structure,
  Codex must not invent a solution and should instead leave the implementation aligned to existing constraints.

## Completion Criteria

An implementation is complete only if all of the following are true:

### Functional Completion
- The full pipeline is implemented in `src/` across the required stages:
  - ingestion
  - normalization
  - classification
  - batch_assignment
  - batch_analysis
  - output_generation
- `pipeline.py` orchestrates the stages in the required order.
- Each stage accepts the correct upstream outputs and produces structured downstream outputs.

### Correctness Completion
- The implementation preserves the global ordering, transitions, and invariants defined by TLA+.
- The implementation applies Dafny-defined local rules consistently across articles and batches.
- Articles that fail normalization or are classified as `reject` do not proceed to downstream analysis.
- Batch assignment respects article-type compatibility and does not mix incompatible article types.
- Batch analysis runs only on valid formed batches.

### Boundary Completion
- Only files under `src/` are modified.
- Read-only sources remain untouched:
  - `Data Pipeline/`
  - `API_documentation/`
  - `LLM Prompts and Schemas/`
  - `agent.md`
  - `architecture.md`
- No new top-level directories are introduced unless explicitly instructed.

### Design Completion
- Module responsibilities remain separated as defined in this repository.
- `pipeline.py` contains orchestration logic only and does not absorb detailed stage logic.
- Shared logic is not duplicated across modules.
- LLM calls are isolated behind clear helper/client boundaries.
- Typed models and explicit domain constants are used for core pipeline objects.

### Failure-Handling Completion
- Expected failure cases are handled explicitly:
  - invalid raw or normalized article data
  - unsupported or rejected classification outcomes
  - incompatible batch assignment cases
  - malformed or incomplete LLM outputs
  - external API or LLM call failures
- Failure handling does not fabricate downstream state.

### Test Completion
- The implementation passes all provided tests.
- If tests are not yet present for a behavior required by TLA+, Dafny, or this agent contract, the code must still implement that behavior faithfully rather than omitting it.
- The implementation must not hardcode behavior solely to satisfy narrow test cases.

### Output Completion
- The pipeline produces both structured internal outputs and user-facing analysis outputs where required.
- Output objects remain stage-appropriate and do not collapse multiple stages into one unstructured representation.

An implementation is not complete if it merely passes tests while violating stage boundaries, formal constraints, domain definitions, or repository structure.

### Ingestion Ambiguity Resolution
Unless explicitly instructed otherwise, Codex should assume:
- synchronous Python stage interfaces
- shared typed models in `src/models.py`
- shared config/constants in `src/config.py`
- explicit HTTP requests for NewsAPI access
- bounded retry handling for 429 and transient failures
- no semantic deduplication during ingestion beyond narrow exact-duplicate suppression if implemented
- explicit preservation of ingestion metadata needed for traceability