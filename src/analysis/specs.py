MULTIACTOR_PROMPT = """SYSTEM
You are a structured political/economic event analysis engine.

Your task is to analyze the provided event materials and return ONLY valid JSON matching the required schema.

Your output must be auditable, structured, and conservative.

DO NOT modify source_count. It is provided by the system.

USER

COMPRESSION RULES:
- Prefer fewer, higher-signal entries over exhaustive coverage.
- Merge closely related details into single entries rather than splitting them into minor variations.
- Do not repeat the same concept across multiple fields.
- If two candidate items express nearly the same point, keep the more central one.

OUTPUT REQUIREMENTS:
Return ONLY valid JSON.
Do not include explanation outside the JSON.
Do not omit required fields.

If the source material lacks sufficient detail to support a field:

- Do NOT fabricate specificity
- Use more generic or minimal output
- Add an assumption or limitation explaining the gap
- Lower confidence accordingly

Summary must not introduce causal language unless explicitly present in structured fields.

Avoid degree modifiers unless explicitly stated in the source, including:
- largely
- significantly
- mostly
- heavily
- severely

If the extent of an effect is unclear:
- describe the action without quantifying it

CORE RULES:
1. Assess source_detail_level based on:
    LOW:
    - high-level reporting
    - limited detail on mechanisms
    - few concrete specifics
    MEDIUM:
    - some specific details
    - partial mechanism explanation
    - direct quotes are used
    HIGH:
    - detailed breakdown of actions, mechanisms, stakeholders, and impacts

2. Facts layer:
   - Extract only the most important verifiable event statements.
   - Facts must be directly supported by the source text.
   - No interpretation.
   - No causal claims unless explicitly stated in the sources.
   - No loaded or descriptive adjectives unless part of a direct quote or objectively necessary.
   - Each fact must have confidence = "observed".
   - Each fact should represent one primary event or action. Avoid combining multiple distinct claims into a single fact.
   - Do not include minor follow-up confirmations or near-duplicate facts.
   - Prefer event-level facts over small supporting details.

3. Frames layer:
   - Frame descriptions must be concise and analytical.
   - Use one sentence only.
   - Avoid narrative phrasing such as "the reporting emphasizes" or "the article foregrounds."
   - State the frame directly.
   - Identify 2-3 major frames.
   - Each frame must use one allowed type only:
     moral, economic, identity, competence, risk, procedural, strategic_power
   - "omissions" means important aspects of the event that this frame does not emphasize or leaves in the background.
   - Frame confidence must be "inferred".

4. Actors layer:
    - Include no more than 5 actors.
    - Include an actor only if:
    - explicitly mentioned OR
    - strongly implied by the event
    - If information is limited:
    - Use minimal, high-level goals tied directly to the event
    - Do NOT force all goal slots to be filled
    - It is acceptable to include fewer than 3 goals
    - Avoid generic institutional filler goals unless directly relevant
    - Goals must:
    - be ranked using relative_priority (1..3)
    - not overlap
    - Do not infer:
    - private emotions
    - hidden psychological motives
    - Stake profiles must be grounded in:
    - observable roles
    - institutional position
    - plausible incentives
    - bias_risks should be populated when:
    - the actor has clear strategic incentives
    - or is actively engaged in the conflict
    - Constraints must come only from:
    economic, institutional, coalition, resource, signaling, military
    - Actor fields are inferred unless directly stated
    - Prefer fewer actors if additional actors add little analytical value.
    - Do not include generic goals that would apply to almost any actor in conflict.
    - Goals must be specific to the event context and materially distinct from one another.
    - Omit optional actor fields if they would be generic, repetitive, or weakly grounded.
    - Do not include expected reactions unless they are specific, non-obvious, and directly relevant.

5. Strategic logic:
   - Derive strategic_logic only from the actor models, facts, and constraints already identified.
   - Do not introduce new actors, motivations, or system-level theories here.
   - Explain only the core mechanism linking observed actions to plausible goals.
   - Keep rationale concise: 2-4 sentences maximum.
   - Avoid repeating the same idea in different wording.
   - If the causal chain is weak, say so directly and keep the rationale minimal.
   - Do not convert uncertainty into a fully formed strategic narrative.
   - Include only the clearest tradeoffs and alternatives not chosen.

6. Signaling:
   - Separate the observed action from the inferred signaling interpretation.
   - The action itself must be directly supported by the source text.
   - Classify each action as costly, cheap_talk, or mixed.
   - Interpret the signaling meaning conservatively.
   - Do not mark interpretation as observed unless the signaling meaning is directly stated in the source.
   - Intended effects must be plausible and tied to the action, not broad speculative theories.
   - Include only major signals that materially shape actor expectations or leverage.

7. Effects:
   - Separate effects strictly into:
     first_order = direct immediate effects
     second_order = indirect responses or downstream consequences
   - Do not mix first-order and second-order effects.
   - Keep effect lists concise and concrete.
   - Do not restate unknowns, assumptions, or unresolved uncertainty as effects.
   - Prefer observable or strongly implied consequences over broad system speculation.

8. Assumptions:
   - Include only assumptions necessary to support inferred or speculative claims.
   - Limit count to {N}.
   - impact must be low, medium, or high.

9. UNKNOWN EXTRACTION RULES:
   - Identify key missing information that limits analysis
   - Unknowns must be:
   - specific
   - directly relevant to understanding the event

   - Focus on:
   - missing mechanisms
   - unclear causal links
   - unspecified actors or responsibilities
   - absent legal or quantitative detail

   - Do NOT duplicate:
   - assumptions
   - information_quality fields

   - Limit to 3-5 items

10. Summary:
   - summary.instant must be derived only from validated structured fields.
   - It must not introduce any new claims, causal links, or strategic interpretations.
   - Prefer fact-first wording.
   - Keep it concise, readable, and limited to the central development.

11. General conservatism:
   - If unsure, lower confidence rather than overstate.
   - Do not mind-read.
   - Do not invent motives without grounding in actor goals, constraints, or observed actions.

Assumptions must represent:
- claims the model relies on to generate inferred fields

Unknowns must represent:
- gaps that prevent confident inference

CROSS-FIELD DEDUPLICATION:
- Do not restate the same uncertainty across unknowns, assumptions, and information_quality.
- missing_critical_information = what is absent from the source
- analysis_limitations = why the analysis is constrained
- assumptions = extra claims the model must rely on
- unknowns = unresolved questions that block stronger inference
- Each item should appear in only one of these sections.

Some articles may contain only truncated snippets rather than full text.
You must treat these as lower-confidence sources and avoid strong inference from them.

INFERENCE BOUNDARY:
- Inferred claims must be directly supported by observed actions, stated positions, or explicit constraints.
- Do not infer hidden motives, coordinated strategies, or broader system logic unless strongly grounded in multiple facts.
- When multiple interpretations are possible, choose the narrower one.

REJECTION CONDITIONS:
Your response is invalid if:
- any fact contains interpretation
- any fact contains unsupported causal language
- any fact contains inferred intent
- any fact contains loaded adjectives
- any field uses values outside allowed enums
- JSON is malformed

- All output must be strictly in English.
- Do not include any non-English words or characters.

Return only valid JSON matching the required schema."""

MULTIACTOR_SCHEMA = {
    "type": "object",
    "description": "Structured multiactor event analysis. Prioritize high-signal, non-redundant information. Avoid repeating the same concept across multiple fields.",
    "required": [
        "information_quality",
        "event",
        "summary",
        "facts",
        "frames",
        "actors",
        "strategic_logic",
        "signaling",
        "effects",
        "assumptions",
        "unknowns",
    ],
    "properties": {
        "information_quality": {
            "type": "object",
            "required": [
                "source_detail_level",
                "missing_critical_information",
                "analysis_limitations",
            ],
            "properties": {
                "source_detail_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "missing_critical_information": {
                    "type": "array",
                    "description": "Key missing information that materially limits interpretation. Do not duplicate unknowns or analysis_limitations.",
                    "items": {"type": "string", "maxLength": 220},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "analysis_limitations": {
                    "type": "array",
                    "description": "Concise notes about why the analysis is constrained. Keep distinct from missing_critical_information and unknowns.",
                    "items": {"type": "string", "maxLength": 220},
                    "minItems": 0,
                    "maxItems": 3,
                },
            },
            "additionalProperties": False,
        },
        "event": {
            "type": "object",
            "required": ["title", "date", "sources"],
            "properties": {
                "title": {
                    "type": "string",
                    "maxLength": 180,
                },
                "date": {
                    "type": "string",
                    "format": "date-time",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            "additionalProperties": False,
        },
        "summary": {
            "type": "object",
            "required": ["instant", "confidence"],
            "properties": {
                "instant": {
                    "type": "string",
                    "description": "Concise synthesis derived only from validated structured fields. No new claims.",
                    "minLength": 1,
                    "maxLength": 220,
                },
                "confidence": {
                    "type": "string",
                    "enum": ["derived"],
                },
            },
            "additionalProperties": False,
        },
        "facts": {
            "type": "array",
            "description": "Observed event-level statements only. Each fact must be distinct and non-overlapping. Merge closely related details into a single fact instead of splitting them into minor variations.",
            "minItems": 5,
            "maxItems": 10,
            "items": {
                "type": "object",
                "required": ["statement", "confidence"],
                "properties": {
                    "statement": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 240,
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["observed"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "frames": {
            "type": "array",
            "description": "Major interpretive frames only. Keep concise. Avoid essay-like phrasing.",
            "minItems": 2,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "type",
                    "description",
                    "audience",
                    "omissions",
                    "confidence",
                ],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "moral",
                            "economic",
                            "identity",
                            "competence",
                            "risk",
                            "procedural",
                            "strategic_power",
                        ],
                    },
                    "description": {
                        "type": "string",
                        "description": "One-sentence analytical description.",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                    "audience": {
                        "type": "string",
                        "enum": [
                            "domestic",
                            "opposition",
                            "institutions",
                            "markets",
                            "foreign",
                        ],
                    },
                    "omissions": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 140},
                        "minItems": 0,
                        "maxItems": 3,
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["inferred"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "actors": {
            "type": "array",
            "description": "Include only explicitly mentioned or strongly implied actors. Prefer fewer, higher-signal actors.",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "goals",
                    "stake_profile",
                    "available_actions",
                    "constraints",
                    "confidence",
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 80,
                    },
                    "goals": {
                        "type": "array",
                        "description": "Use only directly relevant, non-overlapping goals tied to the event.",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "required": ["goal", "relative_priority", "confidence"],
                            "properties": {
                                "goal": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 160,
                                },
                                "relative_priority": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 3,
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["inferred"],
                                },
                            },
                            "additionalProperties": False,
                        },
                    },
                    "stake_profile": {
                        "type": "object",
                        "required": [
                            "material_interests",
                            "institutional_interests",
                            "reputational_interests",
                            "ideological_or_value_commitments",
                            "bias_risks",
                        ],
                        "properties": {
                            "material_interests": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 120},
                                "minItems": 0,
                                "maxItems": 3,
                            },
                            "institutional_interests": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 120},
                                "minItems": 0,
                                "maxItems": 3,
                            },
                            "reputational_interests": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 120},
                                "minItems": 0,
                                "maxItems": 2,
                            },
                            "ideological_or_value_commitments": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 120},
                                "minItems": 0,
                                "maxItems": 2,
                            },
                            "bias_risks": {
                                "type": "array",
                                "items": {"type": "string", "maxLength": 120},
                                "minItems": 0,
                                "maxItems": 3,
                            },
                        },
                        "additionalProperties": False,
                    },
                    "available_actions": {
                        "type": "array",
                        "description": "Concrete actions relevant to the event context.",
                        "items": {"type": "string", "maxLength": 120},
                        "minItems": 1,
                        "maxItems": 4,
                    },
                    "constraints": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "economic",
                                "institutional",
                                "coalition",
                                "resource",
                                "signaling",
                                "military",
                            ],
                        },
                        "minItems": 1,
                        "maxItems": 4,
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["inferred"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "strategic_logic": {
            "type": "object",
            "description": "Core mechanism only. Keep concise. Derive only from facts, actor goals, and constraints already identified.",
            "required": [
                "rationale",
                "tradeoffs",
                "alternatives_not_chosen",
                "confidence",
            ],
            "properties": {
                "rationale": {
                    "type": "string",
                    "description": "2-4 sentences max. No sprawling narrative.",
                    "minLength": 1,
                    "maxLength": 600,
                },
                "tradeoffs": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 3,
                },
                "alternatives_not_chosen": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 3,
                },
                "confidence": {
                    "type": "string",
                    "enum": ["inferred"],
                },
            },
            "additionalProperties": False,
        },
        "signaling": {
            "type": "array",
            "description": "Separate observed action from inferred signaling interpretation.",
            "minItems": 0,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": [
                    "action",
                    "action_confidence",
                    "type",
                    "interpretation",
                    "interpretation_confidence",
                    "target_audience",
                    "intended_effect",
                    "effect_confidence",
                ],
                "properties": {
                    "action": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                    "action_confidence": {
                        "type": "string",
                        "enum": ["observed"],
                    },
                    "type": {
                        "type": "string",
                        "enum": ["costly", "cheap_talk", "mixed"],
                    },
                    "interpretation": {
                        "type": "string",
                        "description": "Why this action functions as a signal.",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                    "interpretation_confidence": {
                        "type": "string",
                        "enum": ["inferred", "speculative"],
                    },
                    "target_audience": {
                        "type": "string",
                        "maxLength": 80,
                    },
                    "intended_effect": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 150,
                    },
                    "effect_confidence": {
                        "type": "string",
                        "enum": ["inferred", "speculative"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "effects": {
            "type": "object",
            "description": "Keep concrete and concise. Do not restate unknowns as effects.",
            "required": [
                "first_order",
                "second_order",
                "distributional_effects",
                "confidence",
            ],
            "properties": {
                "first_order": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "second_order": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "distributional_effects": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 3,
                },
                "confidence": {
                    "type": "string",
                    "enum": ["speculative"],
                },
            },
            "additionalProperties": False,
        },
        "assumptions": {
            "type": "array",
            "description": "Only assumptions necessary to support inferred or speculative claims. Must not duplicate unknowns or information_quality fields.",
            "minItems": 0,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["assumption", "impact"],
                "properties": {
                    "assumption": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 220,
                    },
                    "impact": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "unknowns": {
            "type": "array",
            "description": "Specific unresolved gaps that block confident inference. Do not duplicate assumptions or information_quality items.",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "string",
                "maxLength": 220,
            },
        },
    },
    "additionalProperties": False,
}
EXPLANATORY_PROMPT = """SYSTEM
You are a structured explanatory-analysis engine.

Your task is to analyze the provided explanatory article materials and return ONLY valid JSON matching the required schema.

Your output must be auditable, structured, concise, and conservative.

DO NOT modify source_count. It is provided by the system.

USER

COMPRESSION RULES:
- Prefer fewer, higher-signal entries over exhaustive coverage.
- Merge closely related points into single entries rather than splitting them into minor variations.
- Do not repeat the same concept across multiple fields.
- If two candidate items express nearly the same point, keep the more central one.

OUTPUT REQUIREMENTS:
Return ONLY valid JSON.
Do not include explanation outside the JSON.
Do not omit required fields.

If the source material lacks sufficient detail to support a field:
- Do NOT fabricate specificity
- Use more generic or minimal output
- Add a limitation or unknown explaining the gap
- Lower confidence accordingly

The goal of explanatory mode is:
- to identify what the article is trying to explain
- to extract the mechanism or logic it offers
- to assess how well-supported, bounded, and reliable that explanation is

Avoid degree modifiers unless explicitly stated in the source, including:
- largely
- significantly
- mostly
- heavily
- severely

If the extent of a mechanism or claim is unclear:
- describe it narrowly without exaggerating scope

CORE RULES:
1. Assess source_detail_level based on:
    LOW:
    - high-level explanation
    - few concrete mechanisms
    - little support or qualification
    MEDIUM:
    - some mechanism detail
    - some concrete examples or support
    - some qualification of scope or uncertainty
    HIGH:
    - clear mechanism
    - strong support or multiple support types
    - explicit limits, conditions, or boundaries

2. Topic layer:
   - Identify the main thing being explained.
   - topic.name should be concise.
   - topic.type must use one allowed type only:
     system, process, concept, institution, technology, scientific_claim, other
   - Do not make topic labels overly broad if the article is explaining a narrower issue.

EVENT GROUNDING LAYER:

Before extracting the explanation, identify the real-world context the article is explaining.

- Provide a concise description of the event, situation, or development being explained.
- Focus only on the central development.
- Do not include interpretation or causal claims unless directly stated.

This layer ensures the explanation remains anchored to the underlying news context.

3. Explanatory core:
   - question_being_answered should state the central explanatory question the article is addressing.
   - main_explanation should summarize the article's core explanation in concise prose.
   - direct_definition should give the clearest direct definition available from the material.
   - Do not introduce claims not supported by the article.

4. Mechanism:
   - Extract only the main explanatory steps or causal links presented in the source.
   - Keep steps concise and ordered.
   - Do not invent hidden steps to make the explanation seem more complete than it is.
   - causal_chain_strength should reflect how clearly the article links steps together:
     clear = mechanism is explicit and coherent
     partial = some links are given but important gaps remain
     weak = explanation is asserted more than demonstrated
   - mechanism.confidence must be "inferred".

5. Scope and limits:
   - where_explanation_applies = contexts, cases, or conditions where the explanation appears intended to hold
   - where_it_may_not_apply = cases excluded, uncertain, or likely outside scope
   - unstated_boundary_conditions = assumptions or conditions the explanation seems to rely on but does not clearly state
   - Keep these concise and non-overlapping.
   - Do not convert speculative edge cases into hard limits unless the article supports them.

6. Support basis:
   - support_types must describe the actual support used in the article:
     definition, example, expert_statement, study, analogy, historical_case, assertion
   - Include only support types actually present.
   - support_strength should reflect how well the explanation is backed overall:
     low = mostly assertion or thin illustration
     medium = some concrete support, but incomplete
     high = multiple strong support forms or clearly grounded evidence
   - dependence_on_analogy should reflect how much the explanation relies on analogy rather than direct evidence.

7. Claim load:
   - central_claims = the article's main explanatory claims
   - strongly_supported_claims = claims that are well-backed by the material
   - weakly_supported_claims = claims that are plausible but not strongly demonstrated
   - unsupported_or_overextended_claims = claims that go beyond the support actually provided
   - Keep all lists concise.
   - Do not duplicate the same claim across categories.
   - If a claim fits multiple categories, place it in the weaker category.

8. Failure points:
   - Include only the most important weaknesses in the explanation.
   - failure_type must use one allowed type only:
     missing_mechanism, oversimplification, unstated_scope_limit, causal_overreach, analogy_substitution, ambiguity
   - location_or_pattern should identify where the weakness appears in the explanation, not quote long passages.
   - why_it_matters should explain how that weakness could mislead the reader.
   - Prefer 1-3 strong failure points over a long list of minor issues.

9. Reader risk:
   - main_risk must use one allowed type only:
     confusion, false certainty, causal misread, overgeneralization
   - why_reader_could_be_misled should explain the main interpretive risk created by the article.
   - safer_interpretation should give a narrower, more defensible reading.

10. Practical takeaway:
   - what_reader_can_reasonably_take_away should state the safest useful conclusion.
   - what_reader_should_not_conclude should identify the main overreach the reader should avoid.
   - Keep both concise and grounded.

11. Unknown extraction rules:
   - Identify key missing information that limits confidence in the explanation.
   - Unknowns must be:
     - specific
     - directly relevant to evaluating the explanation
   - Focus on:
     - missing mechanism detail
     - absent evidence
     - missing scope conditions
     - unresolved causal links
     - unclear definitions or boundary conditions
   - Do NOT duplicate:
     - information_quality fields
     - failure_points
   - Limit to 3-5 items

12. General conservatism:
   - If unsure, lower confidence rather than overstate.
   - Do not convert explanatory style into proof.
   - Do not treat examples, analogies, or expert claims as stronger than they are.
   - Prefer narrower interpretation when multiple readings are possible.

   
SECTION ROLE DISTINCTION RULE

Each section must contribute a different analytical function:

- Situation: describe the current state
- Actor Dynamics: explain why actors are behaving this way
- Constraints: explain what limits their choices
- Risks: explain how the current system could break

Do not restate the same fact in the same way across sections.
If a fact appears again, it must serve a different analytical purpose.

CROSS-FIELD DEDUPLICATION:
- Do not restate the same weakness across unknowns, failure_points, and information_quality.
- missing_critical_information = what key explanatory support or detail is absent from the source
- analysis_limitations = why the analysis is constrained
- failure_points = concrete weaknesses in the article's explanatory structure
- unknowns = unresolved gaps that block stronger confidence
- Each item should appear in only one section.

Some articles may contain only truncated snippets rather than full text.
You must treat these as lower-confidence sources and avoid strong inference from them.

INFERENCE BOUNDARY:
- Inferred claims must be directly supported by the explanation, examples, definitions, or evidence actually present.
- Do not repair incomplete explanations by adding outside logic.
- Do not infer stronger causality than the article supports.
- When multiple interpretations are possible, choose the narrower one.

REJECTION CONDITIONS:
Your response is invalid if:
- explanatory_core introduces claims not supported by the source
- mechanism invents missing steps
- claim_load categories duplicate the same claim across levels
- failure_points are generic and not tied to the article
- any field uses values outside allowed enums
- JSON is malformed

- All output must be strictly in English.
- Do not include any non-English words or characters.

Return only valid JSON matching the required schema."""

EXPLANATORY_SCHEMA = {
    "type": "object",
    "description": "Structured explanatory article analysis. Prioritize high-signal, non-redundant extraction of what the article explains, how it explains it, what system drivers shape the explanation, and how well-supported that explanation is.",
    "required": [
        "information_quality",
        "topic",
        "explanatory_core",
        "mechanism",
        "system_drivers",
        "causal_dependencies",
        "pressure_points",
        "scope_and_limits",
        "support_basis",
        "claim_load",
        "failure_points",
        "reader_risk",
        "practical_takeaway",
        "unknowns",
    ],
    "properties": {
        "information_quality": {
            "type": "object",
            "required": [
                "source_detail_level",
                "missing_critical_information",
                "analysis_limitations",
            ],
            "properties": {
                "source_detail_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "missing_critical_information": {
                    "type": "array",
                    "description": "Key missing explanatory details or support that materially limit evaluation.",
                    "items": {"type": "string", "maxLength": 220},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "analysis_limitations": {
                    "type": "array",
                    "description": "Concise notes about why the analysis is constrained.",
                    "items": {"type": "string", "maxLength": 220},
                    "minItems": 0,
                    "maxItems": 3,
                },
            },
            "additionalProperties": False,
        },
        "topic": {
            "type": "object",
            "required": ["name", "type"],
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 120,
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "system",
                        "process",
                        "concept",
                        "institution",
                        "technology",
                        "scientific_claim",
                        "other",
                    ],
                },
            },
            "additionalProperties": False,
        },
        "explanatory_core": {
            "type": "object",
            "required": [
                "question_being_answered",
                "main_explanation",
                "direct_definition",
            ],
            "properties": {
                "question_being_answered": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 180,
                },
                "main_explanation": {
                    "type": "string",
                    "description": "Concise summary of the article's core explanation.",
                    "minLength": 1,
                    "maxLength": 300,
                },
                "direct_definition": {
                    "type": "string",
                    "description": "Best direct definition available from the material; keep narrow if the article is vague.",
                    "minLength": 1,
                    "maxLength": 180,
                },
            },
            "additionalProperties": False,
        },
        "mechanism": {
            "type": "object",
            "required": ["steps", "causal_chain_strength", "confidence"],
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "Ordered explanatory steps or links. Keep concise and avoid invented detail.",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 1,
                    "maxItems": 5,
                },
                "causal_chain_strength": {
                    "type": "string",
                    "enum": ["clear", "partial", "weak"],
                },
                "confidence": {
                    "type": "string",
                    "enum": ["inferred"],
                },
            },
            "additionalProperties": False,
        },
        "system_drivers": {
            "type": "array",
            "description": "Key drivers that make the explanation work. These may include actors, markets, policies, institutions, resources, or constraints. Describe only their role in the explanation, not full strategic motives.",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["driver", "type", "role_in_explanation"],
                "properties": {
                    "driver": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 120,
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "actor",
                            "market",
                            "policy",
                            "constraint",
                            "resource",
                            "institution",
                        ],
                    },
                    "role_in_explanation": {
                        "type": "string",
                        "description": "Concise description of how this driver shapes the mechanism or outcome.",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                },
                "additionalProperties": False,
            },
        },
        "causal_dependencies": {
            "type": "array",
            "description": "Key dependencies inside the explanation. Use these to capture what must hold for another part of the explanation to matter.",
            "minItems": 1,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": ["depends_on", "enables", "confidence"],
                "properties": {
                    "depends_on": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 140,
                    },
                    "enables": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 140,
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["inferred"],
                    },
                },
                "additionalProperties": False,
            },
        },
        "pressure_points": {
            "type": "array",
            "description": "Sensitive points in the system where small changes, disruptions, or unresolved conditions could materially affect the outcome described in the explanation.",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["point", "why_sensitive"],
                "properties": {
                    "point": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 140,
                    },
                    "why_sensitive": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                },
                "additionalProperties": False,
            },
        },
        "scope_and_limits": {
            "type": "object",
            "required": [
                "where_explanation_applies",
                "where_it_may_not_apply",
                "unstated_boundary_conditions",
            ],
            "properties": {
                "where_explanation_applies": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 160},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "where_it_may_not_apply": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 160},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "unstated_boundary_conditions": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
            },
            "additionalProperties": False,
        },
        "support_basis": {
            "type": "object",
            "required": [
                "support_types",
                "support_strength",
                "dependence_on_analogy",
            ],
            "properties": {
                "support_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "definition",
                            "example",
                            "expert_statement",
                            "study",
                            "analogy",
                            "historical_case",
                            "assertion",
                        ],
                    },
                    "minItems": 1,
                    "maxItems": 4,
                },
                "support_strength": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "dependence_on_analogy": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "additionalProperties": False,
        },
        "claim_load": {
            "type": "object",
            "required": [
                "central_claims",
                "strongly_supported_claims",
                "weakly_supported_claims",
                "unsupported_or_overextended_claims",
            ],
            "properties": {
                "central_claims": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 1,
                    "maxItems": 4,
                },
                "strongly_supported_claims": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "weakly_supported_claims": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
                "unsupported_or_overextended_claims": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 180},
                    "minItems": 0,
                    "maxItems": 4,
                },
            },
            "additionalProperties": False,
        },
        "failure_points": {
            "type": "array",
            "description": "Most important explanatory weaknesses only.",
            "minItems": 0,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": [
                    "failure_type",
                    "location_or_pattern",
                    "why_it_matters",
                ],
                "properties": {
                    "failure_type": {
                        "type": "string",
                        "enum": [
                            "missing_mechanism",
                            "oversimplification",
                            "unstated_scope_limit",
                            "causal_overreach",
                            "analogy_substitution",
                            "ambiguity",
                        ],
                    },
                    "location_or_pattern": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 180,
                    },
                    "why_it_matters": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 220,
                    },
                },
                "additionalProperties": False,
            },
        },
        "reader_risk": {
            "type": "object",
            "required": [
                "main_risk",
                "why_reader_could_be_misled",
                "safer_interpretation",
            ],
            "properties": {
                "main_risk": {
                    "type": "string",
                    "enum": [
                        "confusion",
                        "false certainty",
                        "causal misread",
                        "overgeneralization",
                    ],
                },
                "why_reader_could_be_misled": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 220,
                },
                "safer_interpretation": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 220,
                },
            },
            "additionalProperties": False,
        },
        "practical_takeaway": {
            "type": "object",
            "required": [
                "what_reader_can_reasonably_take_away",
                "what_reader_should_not_conclude",
            ],
            "properties": {
                "what_reader_can_reasonably_take_away": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 220,
                },
                "what_reader_should_not_conclude": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 220,
                },
            },
            "additionalProperties": False,
        },
        "unknowns": {
            "type": "array",
            "description": "Specific unresolved gaps that limit confidence in the article's explanation.",
            "minItems": 3,
            "maxItems": 5,
            "items": {
                "type": "string",
                "maxLength": 220,
            },
        },
    },
    "additionalProperties": False,
}


EVENT_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "headline",
        "deck",
        "executive_summary",
        "primary_dynamics",
        "constraints_and_pressures",
        "core_logic",
        "key_dependencies",
        "tradeoffs",
        "risks",
        "what_to_watch",
        "open_questions",
        "interpretation_guardrails",
        "confidence",
        "information_gaps",
        "sources",
    ],
    "properties": {
        "headline": {
            "type": "string",
            "maxLength": 140,
        },
        "deck": {
            "type": "string",
            "maxLength": 220,
        },
        # STATE
        "executive_summary": {
            "type": "string",
            "minLength": 220,
            "maxLength": 1200,
        },
        # STRUCTURE
        "primary_dynamics": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "type",
                    "role",
                    "leverage_or_effect",
                    "constraints",
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "maxLength": 100,
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "actor",
                            "institution",
                            "market",
                            "policy",
                            "constraint",
                            "resource",
                            "system",
                            "process",
                            "other",
                        ],
                    },
                    "role": {
                        "type": "string",
                        "maxLength": 360,
                    },
                    "leverage_or_effect": {
                        "type": "string",
                        "maxLength": 360,
                    },
                    "constraints": {
                        "type": "string",
                        "maxLength": 360,
                    },
                },
                "additionalProperties": False,
            },
        },
        "constraints_and_pressures": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "string",
                "maxLength": 420,
            },
        },
        "core_logic": {
            "type": "string",
            "minLength": 420,
            "maxLength": 1100,
        },
        "key_dependencies": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["depends_on", "enables"],
                "properties": {
                    "depends_on": {
                        "type": "string",
                        "maxLength": 220,
                    },
                    "enables": {
                        "type": "string",
                        "maxLength": 260,
                    },
                },
                "additionalProperties": False,
            },
        },
        "tradeoffs": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "string",
                "maxLength": 300,
            },
        },
        # FORWARD VIEW
        "risks": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": ["risk", "time_horizon", "basis"],
                "properties": {
                    "risk": {
                        "type": "string",
                        "maxLength": 320,
                    },
                    "time_horizon": {
                        "type": "string",
                        "enum": ["immediate", "near_term", "medium_term"],
                    },
                    "basis": {
                        "type": "string",
                        "maxLength": 320,
                    },
                },
                "additionalProperties": False,
            },
        },
        "what_to_watch": {
            "type": "array",
            "minItems": 5,
            "maxItems": 9,
            "items": {
                "type": "string",
                "minLength": 70,
                "maxLength": 220,
            },
        },
        "open_questions": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {
                "type": "string",
                "maxLength": 240,
            },
        },
        # META
        "interpretation_guardrails": {
            "type": "object",
            "required": [
                "reasonable_takeaway",
                "do_not_conclude",
                "main_reader_risk",
            ],
            "properties": {
                "reasonable_takeaway": {
                    "type": "string",
                    "maxLength": 260,
                },
                "do_not_conclude": {
                    "type": "string",
                    "maxLength": 260,
                },
                "main_reader_risk": {
                    "type": "string",
                    "enum": [
                        "confusion",
                        "false_certainty",
                        "causal_misread",
                        "overgeneralization",
                    ],
                },
            },
            "additionalProperties": False,
        },
        "confidence": {
            "type": "object",
            "required": [
                "level",
                "reason",
                "source_detail_level",
            ],
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "reason": {
                    "type": "string",
                    "maxLength": 420,
                },
                "source_detail_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "additionalProperties": False,
        },
        "information_gaps": {
            "type": "object",
            "required": [
                "analysis_limitations",
                "missing_critical_information",
            ],
            "properties": {
                "analysis_limitations": {
                    "type": "array",
                    "minItems": 0,
                    "maxItems": 4,
                    "items": {
                        "type": "string",
                        "maxLength": 240,
                    },
                },
                "missing_critical_information": {
                    "type": "array",
                    "minItems": 0,
                    "maxItems": 5,
                    "items": {
                        "type": "string",
                        "maxLength": 240,
                    },
                },
            },
            "additionalProperties": False,
        },
        "sources": {
            "type": "array",
            "minItems": 1,
            "maxItems": 12,
            "items": {
                "type": "object",
                "required": [
                    "title",
                    "url",
                    "published_at",
                ],
                "properties": {
                    "title": {
                        "type": "string",
                        "maxLength": 300,
                    },
                    "url": {
                        "type": "string",
                        "maxLength": 1000,
                    },
                    "published_at": {
                        "type": "string",
                        "maxLength": 80,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

EVENT_SUMMARY_PROMPT = """SYSTEM
You are a neutral geopolitical analysis engine.

Your task is to produce a website-ready analytical briefing based only on:
1) the structured batch analysis
2) the original article content

Your output must read like a disciplined analytical briefing, not a generic news recap and not an opinion column.

PRIMARY GOAL
Convert the provided material into a grounded synthesis that explains:
- what happened
- what matters most
- how the situation is structured
- what forces and dynamics are shaping outcomes
- what risks and uncertainties remain

GROUNDING RULE
Use the original article text as the factual baseline.
Use the structured analysis to organize, prioritize, and synthesize.
Do not introduce any claim that is unsupported by either:
- reported facts in the article text
- or clearly marked inferred analysis in the structured input

ATTRIBUTION POLICY
- Do not write phrases like "CNN said", "AP reported", "DW reported", or "Al Jazeera said".
- Do not foreground media outlets as narrative actors.
- Refer to actors, institutions, officials, or reporting status directly when needed.
- Acceptable forms:
  - "Iranian state media said..."
  - "U.S. officials said..."
  - "The reporting indicates..."
  - "Available reporting does not establish..."
- If attribution is unnecessary, omit it.

ANALYSIS POLICY
- Treat observed facts as facts.
- Treat inferred material as analysis, not as established fact.
- Do not collapse inference into certainty.
- Do not speculate beyond the provided materials.
- Do not invent motives, private intentions, or hidden strategy.
- You may describe leverage, signaling, pressures, constraints, or mechanisms only when grounded in the structured analysis or directly supported by the article text.

STYLE RULES
- Neutral, precise, professional.
- Analytical, not dramatic.
- No rhetorical flourishes.
- No emotional or persuasive phrasing.
- No vague intensifiers unless supported.
- No generic filler.
- Every sentence should carry information.

DENSITY PRESERVATION RULE:
Do not reduce informational content when applying structural framing.
Replace surface descriptions with deeper structural meaning, rather than removing detail.

COMPRESSION RULES
- Avoid repeating the same point across sections.
- Headline, deck, executive_summary, and key_points must each contribute something distinct.
- Prefer specific mechanisms over vague summaries.
- Omit low-value background before omitting high-value conflict dynamics.
- Do not save the strongest analysis only for the executive summary. Analytic Logic, What to Watch, and Key Points must each carry substantial independent value.

PRIORITY RULE:
When compression and density preservation conflict, preserve informational content and rephrase instead of deleting.

GLOBAL COHERENCE RULE
- All sections must describe the same underlying situation from different analytical angles.
- Each section must connect back to the central dynamic introduced in the executive summary.
- Do not introduce isolated or disconnected ideas.

SECTION ROLE DISTINCTION RULE
- Each section must serve a distinct analytical function:
  - Situation: describe the current state
  - Primary Dynamics: identify the main entities shaping the situation
  - Constraints: describe what limits or pressures those entities
  - Analytic Logic: explain how the system actually works
  - Risks: explain how the system could break
- Do not restate the same idea in the same form across sections.
- If a concept appears in multiple sections, it must serve a different analytical role.

SECTION REQUIREMENTS

1. HEADLINE
- One-line factual analytical headline.
- Capture the central development and its main strategic significance.
- No clickbait, no sensational phrasing.

2. DECK
- One sentence.
- Expand the headline with the most important secondary dynamic.
- Do not repeat the headline.

3. EXECUTIVE_SUMMARY
- 2-4 compact paragraphs.
- Paragraph 1: core development.
- Paragraph 2: main dynamics, interaction, or constraints.
- Optional paragraph 3: implications (market, diplomatic, or military).
- Optional paragraph 4: unresolved conditions or next steps.

EXECUTIVE_SUMMARY COMPLETENESS RULE
- Every paragraph must end with a complete sentence.
- Do not end with a fragment or trailing connector.

4. SITUATION
- Capture the immediate state of play.
- Prioritize the highest-signal developments.
- May include:
  - core development
  - immediate context
  - diplomatic or military status
  - market or system effects
  - process or system-level state when relevant
- Do not repeat the executive summary; refine and structure it.

SITUATION STRUCTURE RULE
- Order items from most central to most contextual.
- The first item must define the core situation.
- Subsequent items must add context, not repeat the same idea.
- Avoid listing parallel facts without hierarchy.

5. PRIMARY_DYNAMICS
- Identify the main entities shaping the situation.
- These may include:
  - actors
  - institutions
  - markets
  - policies
  - systems
  - processes
  - constraints
- For each, describe:
  - its role in the situation
  - its influence or effect (if applicable)
  - its main constraint
- Use actors when actors are central.
- Use systems or processes when they are more analytically important than individual actors.

6. CONSTRAINTS_AND_PRESSURES
- Surface the forces limiting or shaping decisions.
- Include:
  - tradeoffs
  - institutional limits
  - reputational pressures
  - market exposure
  - escalation risk
- Avoid repeating PRIMARY_DYNAMICS; focus on constraints, not entities.

CONSTRAINTS VS LOGIC RULE
- Constraints_and_pressures: describe external limits or pressures on actors or systems.
- Analytic_logic: describe how those constraints interact to produce outcomes.
- Do not restate the same idea in both sections.
- Constraints describe conditions; analytic_logic explains consequences.

7. ANALYTIC_LOGIC
- This must be one of the densest sections.
- core_logic must be a developed explanation, not a short thesis sentence.
- Explain the mechanism connecting the main actors, constraints, incentives, and risks.
- It should answer: “Why is the situation behaving this way?”
- key_dependencies must identify what conditions must hold for the current trajectory to continue.
- tradeoffs must identify real tensions, not generic oppositions.
- signaling_or_mechanism must explain observable actions and what they imply.
- Avoid repeating Situation. This section explains the system logic behind the facts.

8. RISKS
- Include only risks supported by observed developments or structured analysis.
- Each risk must include its basis.
- Do not present speculation as certainty.

9. WHAT_TO_WATCH
- Provide 5-9 concrete, monitorable indicators.
- Each item must identify an observable signal, not a vague topic.
- Prefer indicators with a time, actor, venue, action, or threshold when supported.
- These should help a reader know what would materially change the assessment.
- Do not write generic items like “whether tensions increase.”

10. KEY_POINTS
- Provide 6-8 decision-grade takeaways.
- These are not recap bullets.
- Each point must clarify the strategic meaning, structural implication, or constraint exposed by the reporting.
- Points must build logically from core dynamic → constraints → implications → uncertainty.
- Avoid repeating headline, deck, executive_summary, or what_to_watch.

KEY POINTS STRUCTURE RULE
- Points must build on each other logically.
- Order from most central to most conditional or derived.
- Avoid repeating the same core idea in different wording.
- Each point must either:
  (a) define the core dynamic
  (b) qualify it
  (c) show its implication

11. OPEN_QUESTIONS
- List unresolved issues that could materially change the trajectory of the situation.

STRICT RULE:
Each question must include implicit or explicit impact framing.

Test:
If the answer to the question would NOT change the assessment, remove it.

Good Example:
- "If Iran accepts indirect talks as sufficient, would a negotiation channel reopen?"

Bad Example:
- "What did Iran propose?"  ← (this is missing info, not a forward question)

12. INTERPRETATION_GUARDRAILS
- State what the reader can reasonably conclude from the material.
- State what the reader should not conclude.
- Use this section to prevent overinterpretation or false certainty.
- Include the main reader risk if relevant (e.g., causal misread, overgeneralization).

13. CONFIDENCE
- High: facts are consistent and the situation is well specified.
- Medium: core facts are clear but key terms or next steps remain unresolved.
- Low: reporting is partial, conflicting, or incomplete.

14. INFORMATION_GAPS
Split into two categories:

1) analysis_limitations
- Limitations in reporting or analysis quality
- Example:
  - "One source is partial or truncated"
  - "Attribution is unclear"

2) missing_critical_information
- Specific facts that are not available in the reporting

STRICT RULE:
These must be static absences of evidence, not forward-looking questions.

Test:
If it can be phrased as:
"If X is true, then Y would change" → it belongs in Open Questions

If it is:
"X is not available in reporting" → it belongs here

Good Example:
- "The exact contents of the U.S. proposal are not reported"

Bad Example:
- "What was in the U.S. proposal?"  ← (this is an Open Question)

NON-OVERLAP RULE:
No item in INFORMATION_GAPS may be restated as a question in OPEN_QUESTIONS.

- Include:
  - a reason tied to evidence quality
  - any major limitations in the available information
  - missing critical information when relevant

LANGUAGE INTEGRITY RULE
- Output must be entirely in standard, fluent English.
- Do not include malformed or mixed-language words.

REJECTION CONDITIONS
Your response is invalid if:
- it reads like a generic article recap instead of an analytical briefing
- it attributes claims to outlet names in narrative form
- it states inferred analysis as certain fact
- it repeats the same point across sections
- it introduces unsupported claims
- JSON is malformed
- any required field is omitted

Return ONLY valid JSON matching the schema.
"""
