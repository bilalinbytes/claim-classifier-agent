"""Unit tests for tool execution and security constraints."""
import pytest
from src.tools import execute_tool_call, ToolExecutionError
from src.config import FACT_VERSION


def test_execute_get_brand_facts_valid(brand_facts_dict):
    known_brands = {"cleartrail", "cloudnote", "stonewave"}
    result = execute_tool_call(
        tool_name="get_brand_facts",
        arguments={"brand_id": "cleartrail"},
        brand_facts=brand_facts_dict,
        known_brands=known_brands,
    )
    assert result["fact_version"] == FACT_VERSION
    assert result["brand_id"] == "cleartrail"
    assert len(result["facts"]) > 0
    assert all(f["brand_id"] == "cleartrail" for f in result["facts"])


def test_execute_unknown_brand(brand_facts_dict):
    known_brands = {"cleartrail", "cloudnote", "stonewave"}
    with pytest.raises(ToolExecutionError, match="Unknown requested brand"):
        execute_tool_call(
            tool_name="get_brand_facts",
            arguments={"brand_id": "unsupported_brand"},
            brand_facts=brand_facts_dict,
            known_brands=known_brands,
        )


def test_execute_illegal_tool_name(brand_facts_dict):
    known_brands = {"cleartrail", "cloudnote", "stonewave"}
    with pytest.raises(ToolExecutionError, match="Illegal tool"):
        execute_tool_call(
            tool_name="system_exec",
            arguments={"cmd": "ls"},
            brand_facts=brand_facts_dict,
            known_brands=known_brands,
        )


def test_execute_malformed_arguments(brand_facts_dict):
    known_brands = {"cleartrail", "cloudnote", "stonewave"}
    with pytest.raises(ToolExecutionError, match="Missing or invalid 'brand_id'"):
        execute_tool_call(
            tool_name="get_brand_facts",
            arguments={},
            brand_facts=brand_facts_dict,
            known_brands=known_brands,
        )
