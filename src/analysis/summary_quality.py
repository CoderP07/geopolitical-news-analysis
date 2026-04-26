from dataclasses import dataclass, field
import os
from typing import Any
from copy import deepcopy
import re
import unicodedata
import json
from openai import OpenAI


@dataclass
class ValidationIssue:
    path: str
    issue_type: str
    message: str
    severity: str
    original_text: str | None = None
    normalized_text: str | None = None


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class RepairInstruction:
    path: str
    reason: str
    current_text: str


@dataclass
class FinalizationResult:
    is_valid: bool
    final_json: dict[str, Any] | None
    initial_validation: ValidationResult
    final_validation: ValidationResult | None = None
    repair_attempted: bool = False
    failure_reason: str | None = None


def should_skip_language_style_checks(path: str) -> bool:
    return path.endswith(".actor")


def contains_disallowed_script(text: str) -> bool:
    for ch in text:
        if not ch.isalpha():
            continue

        name = unicodedata.name(ch, "")

        if "LATIN" in name:
            continue

        # any alphabetic non-Latin char is invalid
        return True

    return False


def find_disallowed_script_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    return [token for token in tokens if contains_disallowed_script(token)]


def get_text_at_path(summary_json: dict, path: str) -> Any:
    current = summary_json

    # split by dots but keep indices
    parts = re.split(r"\.(?![^\[]*\])", path)

    for part in parts:
        match = re.match(r"(\w+)\[(\d+)\]", part)
        if match:
            key = match.group(1)
            index = int(match.group(2))
            current = current.get(key, [])
            if not isinstance(current, list) or index >= len(current):
                return None
            current = current[index]
        else:
            if not isinstance(current, dict):
                return None
            current = current.get(part)

        if current is None:
            return None

    return current


def set_text_at_path(summary_json: dict, path: str, value: Any) -> None:
    current = summary_json

    parts = re.split(r"\.(?![^\[]*\])", path)

    for part in parts[:-1]:
        match = re.match(r"(\w+)\[(\d+)\]", part)
        if match:
            key = match.group(1)
            index = int(match.group(2))
            current = current[key][index]
        else:
            current = current[part]

    last = parts[-1]
    match = re.match(r"(\w+)\[(\d+)\]", last)

    if match:
        key = match.group(1)
        index = int(match.group(2))
        current[key][index] = value
    else:
        current[last] = value


def iter_summary_text_fields(summary_json: dict) -> list[tuple[str, str]]:
    fields = []

    fields.append(("headline", summary_json.get("headline", "")))
    fields.append(("deck", summary_json.get("deck", "")))
    fields.append(("executive_summary", summary_json.get("executive_summary", "")))

    for i, item in enumerate(summary_json.get("situation", [])):
        fields.append((f"situation[{i}].text", item.get("text", "")))

    for i, item in enumerate(summary_json.get("actor_dynamics", [])):
        fields.append((f"actor_dynamics[{i}].actor", item.get("actor", "")))
        fields.append((f"actor_dynamics[{i}].position", item.get("position", "")))
        fields.append((f"actor_dynamics[{i}].leverage", item.get("leverage", "")))
        fields.append((f"actor_dynamics[{i}].constraints", item.get("constraints", "")))

    for i, text in enumerate(summary_json.get("constraints_and_pressures", [])):
        fields.append((f"constraints_and_pressures[{i}]", text))

    for i, item in enumerate(summary_json.get("risks", [])):
        fields.append((f"risks[{i}].risk", item.get("risk", "")))
        fields.append((f"risks[{i}].basis", item.get("basis", "")))

    for i, text in enumerate(summary_json.get("what_to_watch", [])):
        fields.append((f"what_to_watch[{i}]", text))

    for i, text in enumerate(summary_json.get("key_points", [])):
        fields.append((f"key_points[{i}]", text))

    for i, text in enumerate(summary_json.get("open_questions", [])):
        fields.append((f"open_questions[{i}]", text))

    confidence = summary_json.get("confidence", {})
    fields.append(("confidence.reason", confidence.get("reason", "")))

    return fields


MOJIBAKE_PATTERNS = [
    "â€™",
    "â€œ",
    "â€",
    "Ã",
    "Â",
    "�",
]

INCOMPLETE_ENDING_WORDS = {
    "and",
    "or",
    "but",
    "that",
    "which",
    "because",
    "while",
    "although",
    "however",
    "therefore",
    "thus",
    "to",
    "of",
    "in",
    "if",
    "on",
    "at",
    "by",
    "for",
    "with",
    "from",
    "into",
    "about",
    "the",
    "a",
    "an",
}


def is_prose_field(path: str) -> bool:
    prose_prefixes = [
        "deck",
        "executive_summary",
        "confidence.reason",
    ]
    if path in prose_prefixes:
        return True

    prose_contains = [
        ".text",
        ".position",
        ".leverage",
        ".constraints",
        ".basis",
    ]
    return any(part in path for part in prose_contains)


def contains_unwanted_control_chars(text: str) -> bool:
    for ch in text:
        if unicodedata.category(ch) == "Cc" and ch not in "\n\t\r":
            return True
    return False


def contains_zero_width_chars(text: str) -> bool:
    zero_width = {
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\ufeff",  # BOM
    }
    return any(ch in zero_width for ch in text)


def token_has_mixed_script(token: str) -> bool:
    has_latin = False
    has_cyrillic = False
    has_greek = False

    for ch in token:
        if not ch.isalpha():
            continue
        name = unicodedata.name(ch, "")
        if "LATIN" in name:
            has_latin = True
        elif "CYRILLIC" in name:
            has_cyrillic = True
        elif "GREEK" in name:
            has_greek = True

    script_count = sum([has_latin, has_cyrillic, has_greek])
    return script_count >= 2


def find_mixed_script_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    return [token for token in tokens if token_has_mixed_script(token)]


def has_incomplete_ending(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    if stripped[-1] in {",", ":", ";", "-", "(", "[", "{", "/"}:
        return True

    words = re.findall(r"[A-Za-z']+", stripped.lower())
    if not words:
        return False

    last_word = words[-1]
    if last_word in INCOMPLETE_ENDING_WORDS:
        return True

    if stripped.count("(") > stripped.count(")"):
        return True
    if stripped.count('"') % 2 == 1:
        return True

    return False


def validate_summary_content(summary_json: dict) -> ValidationResult:
    issues: list[ValidationIssue] = []

    for path, text in iter_summary_text_fields(summary_json):
        if not isinstance(text, str):
            issues.append(
                ValidationIssue(
                    path=path,
                    issue_type="non_string_field",
                    message="Field is not a string.",
                    severity="high",
                    original_text=str(text),
                )
            )
            continue

        if not text.strip():
            issues.append(
                ValidationIssue(
                    path=path,
                    issue_type="empty_text",
                    message="Field is empty or whitespace only.",
                    severity="high",
                    original_text=text,
                )
            )
            continue

        normalized = unicodedata.normalize("NFC", text)

        if normalized != text:
            issues.append(
                ValidationIssue(
                    path=path,
                    issue_type="unicode_normalization_needed",
                    message="Field is not in normalized Unicode form.",
                    severity="low",
                    original_text=text,
                    normalized_text=normalized,
                )
            )

        if contains_unwanted_control_chars(text):
            issues.append(
                ValidationIssue(
                    path=path,
                    issue_type="control_characters",
                    message="Field contains disallowed control characters.",
                    severity="high",
                    original_text=text,
                )
            )

        if contains_zero_width_chars(text):
            issues.append(
                ValidationIssue(
                    path=path,
                    issue_type="zero_width_characters",
                    message="Field contains zero-width or invisible characters.",
                    severity="medium",
                    original_text=text,
                )
            )

        for pattern in MOJIBAKE_PATTERNS:
            if pattern in text:
                issues.append(
                    ValidationIssue(
                        path=path,
                        issue_type="mojibake",
                        message=f"Field contains mojibake pattern: {pattern}",
                        severity="high",
                        original_text=text,
                    )
                )
                break

        if not should_skip_language_style_checks(path):

            mixed_tokens = find_mixed_script_tokens(text)
            if mixed_tokens:
                issues.append(
                    ValidationIssue(
                        path=path,
                        issue_type="mixed_script_token",
                        message=f"Field contains mixed-script token(s): {', '.join(mixed_tokens[:3])}",
                        severity="high",
                        original_text=text,
                    )
                )

            disallowed_tokens = find_disallowed_script_tokens(text)
            if disallowed_tokens:
                issues.append(
                    ValidationIssue(
                        path=path,
                        issue_type="disallowed_script_token",
                        message=f"Field contains disallowed-script token(s): {', '.join(disallowed_tokens[:3])}",
                        severity="high",
                        original_text=text,
                    )
                )
            elif contains_disallowed_script(text):
                issues.append(
                    ValidationIssue(
                        path=path,
                        issue_type="disallowed_script_token",
                        message="Field contains non-Latin alphabetic characters.",
                        severity="high",
                        original_text=text,
                    )
                )

            if is_prose_field(path) and has_incomplete_ending(text):
                issues.append(
                    ValidationIssue(
                        path=path,
                        issue_type="incomplete_ending",
                        message="Field appears to end with an incomplete clause or dangling punctuation.",
                        severity="medium",
                        original_text=text,
                    )
                )
    return ValidationResult(
        is_valid=(len(issues) == 0),
        issues=issues,
    )


ZERO_WIDTH_CHARS = {
    "\u200b",  # zero width space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\ufeff",  # BOM
}

MOJIBAKE_REPLACEMENTS = {
    "â€™": "’",
    "â€œ": "“",
    "â€\x9d": "”",
    "â€": "-",
    "Â ": " ",
    "Â": "",
}


def clean_text_deterministically(text: str) -> str:
    if not isinstance(text, str):
        return text

    cleaned = text

    # Unicode normalization
    cleaned = unicodedata.normalize("NFC", cleaned)

    # Remove zero-width characters
    cleaned = "".join(ch for ch in cleaned if ch not in ZERO_WIDTH_CHARS)

    # Remove disallowed control characters, keep normal whitespace controls
    cleaned = "".join(
        ch for ch in cleaned if unicodedata.category(ch) != "Cc" or ch in "\n\t\r"
    )

    # Replace known mojibake patterns
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        cleaned = cleaned.replace(bad, good)

    # Normalize whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Remove space before punctuation
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)

    return cleaned.strip()


def deterministic_cleanup(summary_json: dict[str, Any]) -> dict[str, Any]:
    cleaned = deepcopy(summary_json)

    if "headline" in cleaned:
        cleaned["headline"] = clean_text_deterministically(cleaned["headline"])
    if "deck" in cleaned:
        cleaned["deck"] = clean_text_deterministically(cleaned["deck"])
    if "executive_summary" in cleaned:
        cleaned["executive_summary"] = clean_text_deterministically(
            cleaned["executive_summary"]
        )

    for item in cleaned.get("situation", []):
        if "text" in item:
            item["text"] = clean_text_deterministically(item["text"])

    for item in cleaned.get("actor_dynamics", []):
        for key in ["actor", "position", "leverage", "constraints"]:
            if key in item:
                item[key] = clean_text_deterministically(item[key])

    for i, text in enumerate(cleaned.get("constraints_and_pressures", [])):
        cleaned["constraints_and_pressures"][i] = clean_text_deterministically(text)

    for item in cleaned.get("risks", []):
        for key in ["risk", "basis"]:
            if key in item:
                item[key] = clean_text_deterministically(item[key])

    for list_key in ["what_to_watch", "key_points", "open_questions"]:
        for i, text in enumerate(cleaned.get(list_key, [])):
            cleaned[list_key][i] = clean_text_deterministically(text)

    confidence = cleaned.get("confidence")
    if isinstance(confidence, dict) and "reason" in confidence:
        confidence["reason"] = clean_text_deterministically(confidence["reason"])

    return cleaned


REPAIRABLE_ISSUE_TYPES = {
    "mixed_script_token",
    "incomplete_ending",
    "empty_text",
    "mojibake",
    "disallowed_script_token",
}


def extract_repair_requests(
    summary_json: dict[str, Any],
    validation_result: ValidationResult,
) -> list[RepairInstruction]:
    repairs: list[RepairInstruction] = []
    seen_paths: set[str] = set()

    for issue in validation_result.issues:
        if issue.issue_type not in REPAIRABLE_ISSUE_TYPES:
            continue

        if issue.path in seen_paths:
            continue

        current_text = get_text_at_path(summary_json, issue.path)
        if not isinstance(current_text, str):
            continue

        repairs.append(
            RepairInstruction(
                path=issue.path,
                reason=issue.message,
                current_text=current_text,
            )
        )
        seen_paths.add(issue.path)

    return repairs


def build_repair_prompt(repairs: list[RepairInstruction]) -> str:
    header = """
You are a precision text repair system.

You will receive a list of fields that contain errors.
Each field includes:
- path
- reason
- current_text

Your task:
- Fix ONLY the text
- Preserve meaning
- Ensure fluent, correct English
- Do NOT add new information
- Do NOT change structure
- Do NOT modify any field not listed

- All output must be strictly in English
- Do not include any non-English words or characters

Return ONLY valid JSON in this format:

{
"repairs": [
    {
    "path": "...",
    "replace_with": "..."
    }
]
}

FIELDS:
""".strip()

    field_blocks = []

    for i, r in enumerate(repairs, start=1):
        field_blocks.append(
            f"""{i}.
path: {r.path}
reason: {r.reason}
current_text: {r.current_text}
"""
        )

    return header + "\n\n" + "\n".join(field_blocks)


REPAIR_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["repairs"],
    "properties": {
        "repairs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "replace_with"],
                "properties": {
                    "path": {"type": "string"},
                    "replace_with": {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}


def apply_field_repairs(
    summary_json: dict[str, Any],
    repairs: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = deepcopy(summary_json)

    for repair in repairs:
        path = repair.get("path")
        replace_with = repair.get("replace_with")

        if not isinstance(path, str):
            continue
        if not isinstance(replace_with, str):
            continue

        # Optional safety: only apply to known existing fields
        existing_value = get_text_at_path(updated, path)
        if existing_value is None:
            continue

        set_text_at_path(updated, path, replace_with)

    return updated


def finalize_summary_json(
    llm_result: dict[str, Any],
    client: OpenAI,
    model: str = "gpt-5.4-mini",
) -> FinalizationResult:

    cleaned = deterministic_cleanup(llm_result)
    initial_validation = validate_summary_content(cleaned)

    if initial_validation.is_valid:
        return FinalizationResult(
            is_valid=True,
            final_json=cleaned,
            initial_validation=initial_validation,
            repair_attempted=False,
        )

    repair_requests = extract_repair_requests(cleaned, initial_validation)

    if not repair_requests:
        return FinalizationResult(
            is_valid=False,
            final_json=None,
            initial_validation=initial_validation,
            repair_attempted=False,
            failure_reason="no_repairable_issues",
        )

    try:
        repair_prompt = build_repair_prompt(repair_requests)

        repair_response = client.responses.create(
            model=model,
            reasoning={"effort": "low"},
            input=repair_prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "summary_repairs",
                    "strict": True,
                    "schema": REPAIR_RESPONSE_SCHEMA,
                }
            },
        )

        repair_json = json.loads(repair_response.output_text)

        repaired = apply_field_repairs(cleaned, repair_json["repairs"])
        repaired = deterministic_cleanup(repaired)

        final_validation = validate_summary_content(repaired)

        if final_validation.is_valid:
            return FinalizationResult(
                is_valid=True,
                final_json=repaired,
                initial_validation=initial_validation,
                final_validation=final_validation,
                repair_attempted=True,
            )

        return FinalizationResult(
            is_valid=False,
            final_json=None,
            initial_validation=initial_validation,
            final_validation=final_validation,
            repair_attempted=True,
            failure_reason="repair_failed_validation",
        )

    except Exception as e:
        return FinalizationResult(
            is_valid=False,
            final_json=None,
            initial_validation=initial_validation,
            repair_attempted=True,
            failure_reason=f"exception: {str(e)}",
        )


if __name__ == "__main__":
    from openai import OpenAI

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY is not set")
    client = OpenAI(api_key=openai_key)

    # Paste your JSON here (exactly as dict, not string)
    test_summary = {}

    result = finalize_summary_json(test_summary, client)
    print("\n--- INITIAL VALIDATION ISSUES ---")
    for issue in result.initial_validation.issues:
        print(f"{issue.path} | {issue.issue_type} | {issue.message}")

    if result.final_validation is not None:
        print("\n--- FINAL VALIDATION ISSUES ---")
        if result.final_validation.issues:
            for issue in result.final_validation.issues:
                print(f"{issue.path} | {issue.issue_type} | {issue.message}")
        else:
            print("None")
    print("\n--- FINALIZATION RESULT ---")
    print("Valid:", result.is_valid)
    print("Repair attempted:", result.repair_attempted)
    print("Failure reason:", result.failure_reason)
    print("\n--- BEFORE EXECUTIVE SUMMARY ---")
    print(test_summary["executive_summary"])

    if result.final_json:
        print("\n--- AFTER EXECUTIVE SUMMARY ---")
        print(result.final_json["executive_summary"])
    if result.final_json:
        print("\n--- FINAL JSON ---")
        print(json.dumps(result.final_json, indent=2, ensure_ascii=False))
