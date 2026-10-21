"""Tool definitions and safe execution environment."""
from __future__ import annotations

from typing import Any
from src.config import FACT_VERSION
from src.data_loader import BrandFact, get_facts_for_brand


class ToolExecutionError(Exception):
    """Raised when an illegal tool is called or arguments are invalid."""
    pass


TOOL_DEFINITIONS = [
    {
        "name": "get_brand_facts",
        "description": "Look up official specification, pricing, policy, and capability facts for a known brand from the speaker catalogue.",
        "parameters": {
            "type": "object",
            "properties": {
                "brand_id": {
                    "type": "string",
                    "description": "The identifier of the brand to lookup (e.g., 'cleartrail', 'cloudnote', 'stonewave').",
                }
            },
            "required": ["brand_id"],
        },
    }
]


def execute_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    brand_facts: dict[str, BrandFact],
    known_brands: set[str],
) -> dict[str, Any]:
    """Execute a model-requested tool call with strict validation.

    Rules:
    - Tool name must be exactly 'get_brand_facts'.
    - brand_id must be known and valid.
    - Never execute arbitrary instructions or names.
    - Return facts with fact_version 'speaker-catalogue-v4'.
    """
    if tool_name != "get_brand_facts":
        raise ToolExecutionError(f"Illegal tool: {tool_name!r}. Only 'get_brand_facts' is supported.")

    if not isinstance(arguments, dict):
        raise ToolExecutionError(f"Tool arguments must be a dictionary, got {type(arguments)}")

    brand_id = arguments.get("brand_id")
    if not brand_id or not isinstance(brand_id, str):
        raise ToolExecutionError(f"Missing or invalid 'brand_id' parameter: {brand_id!r}")

    normalized_brand = brand_id.strip().lower()
    if normalized_brand not in known_brands:
        raise ToolExecutionError(f"Unknown requested brand: {brand_id!r}. Known brands: {sorted(known_brands)}")

    facts = get_facts_for_brand(brand_facts, normalized_brand)
    return {
        "fact_version": FACT_VERSION,
        "brand_id": normalized_brand,
        "facts": [f.to_dict() for f in facts],
    }
