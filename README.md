# Geopolitical News Analysis Pipeline

## Overview

This project is a structured pipeline for analyzing _ specific geopolitical news.

The pipeline ingests articles from specified sources, classifies them by type, groups them into coherent batches, and generates structured event briefings using LLMs. 

## Motivation

Modern news coverage is often fragmented across sources, with each article emphasizing a narrow slice of a broader event.

This leads to readers mentally reconstructing the full situation from partial and sometimes conflicting narratives.

This project treats geopolitical events as systems rather than isolated reports.

The goal is to:
- aggregate multiple perspectives
- extract underlying dynamics and constraints
- present events as structured, analyzable scenarios rather than narrative fragments

By focusing on structure over rhetoric, the system aims to support clearer reasoning and more informed discussion of current events.

This approach also enables a shift from continuous monitoring to periodic understanding, allowing readers to engage with events in coherent updates rather than reacting to a constant stream of fragmented information.

The system is designed to shift attention from how events are described to how they actually function.

## Key Idea

Most LLM outputs are highly variable or unstructured

This system attempts to enfoce:
- strict classification rules
- structured schemas
- multi-stage preprocessing'

the result is a consistent, decision-oriented analysis.

## Pipeline

1. **Ingest**
   - Pulls articles from NewsAPI

2. **Normalize**
   - Extracts full text
   - Filters for relevance

3. **Classify**
   - Labels each article (multiactor, explanatory, etc.)
   
4. **Batch**
   - Groups related articles into coherent sets based on their classification 
   
5. **Analyze**
   - Runs LLM analysis with strict JSON schemas

6. **Summarize**
   - Produces structured event briefings for the frontend

## Output

Each event briefing includes:
- Confidence Assessment
- Executive Summary
- Primary Dynamics
- Constraints and Pressures
- Core Logic
- Key Dependencies
- Tradeoffs
- Risks
- Constraints
- Risks
- What to watch
- Open Questions
- Interpretation Guardrails
- Information Gaps
- Sources

The frontend presents this as a clean, structured analysis interface.

## Stack

- Python (pipeline)
- PostgreSQL (storage)
- FastAPI (API)
- TailwindCSS (frontend)
- OpenAI API (LLM analysis)

## Future Work

- Generate causal maps from structured outputs
- Add interactive visualization layer
- Improve cross-event linking and trend detection
- Improve deterministic classification and category weights
- Select specialized LLM models for each task (e.g., classification, event analysis, and final summary) instead of using GPT-5.4-mini for all steps
- Expand into political actor analysis as the election cycle approaches 

## Reliability and Quality Controls

The system includes layered validation and repair mechanisms to ensure output quality and consistency:

- **Deterministic Cleanup**
  - Normalizes Unicode, removes malformed characters, and fixes common encoding issues
  - Ensures consistent text formatting before validation

- **Structured Validation**
  - Validates all output fields for completeness, formatting, and language consistency
  - Detects issues such as incomplete endings, invalid characters, or malformed text

- **Targeted LLM Repair Pass**
  - Triggered only when validation fails
  - Repairs specific fields rather than regenerating the full summary
  - Uses a strict JSON schema to enforce safe, controlled modifications

- **Re-Validation**
  - Re-checks all repaired outputs to ensure issues are fully resolved
  - Rejects outputs that still fail validation

- **Schema Enforcement**
  - All LLM outputs must conform to strict JSON schemas
  - This prevents structural drift and ensures consistency across analyses

- This approach reduces unnecessary LLM calls while maintaining high output reliability
