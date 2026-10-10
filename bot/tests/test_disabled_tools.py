# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""tools.disabled_tools removes tools for every agent, subagent and MCP registration."""

import asyncio
from typing import Any

from vikingbot.agent.tools.base import Tool
from vikingbot.agent.tools.factory import register_default_tools, register_subagent_tools
from vikingbot.agent.tools.registry import ToolRegistry
from vikingbot.config.schema import Config, SessionKey

DISABLED = ["exec", "write_file", "edit_file", "mcp_github_create_issue"]


class _NamedTool(Tool):
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "test tool"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, tool_context, **kwargs: Any) -> str:
        return "ok"


def _names(registry: ToolRegistry) -> set[str]:
    return {tool["function"]["name"] for tool in registry.get_definitions()}


def test_default_config_keeps_upstream_tools():
    config = Config()
    registry = ToolRegistry(config=config)
    register_default_tools(registry, config)
    assert {"exec", "write_file", "edit_file", "read_file"} <= _names(registry)


def test_disabled_tools_are_not_registered_for_agent_or_subagent():
    config = Config(tools={"disabled_tools": DISABLED})

    registry = ToolRegistry(config=config)
    register_default_tools(registry, config)
    names = _names(registry)
    assert names.isdisjoint(DISABLED)
    assert {"read_file", "list_dir", "web_search"} <= names
    assert not registry.has("exec")

    subagent = ToolRegistry(config=config)
    register_subagent_tools(subagent, config)
    assert _names(subagent).isdisjoint(DISABLED)
    assert subagent.has("read_file")


def test_disabled_tools_apply_to_mcp_wrappers_and_execution():
    config = Config(tools={"disabled_tools": DISABLED})
    registry = ToolRegistry(config=config)
    registry.register(_NamedTool("mcp_github_create_issue"))
    registry.register(_NamedTool("mcp_github_search_issues"))
    assert _names(registry) == {"mcp_github_search_issues"}

    result = asyncio.run(
        registry.execute_detailed(
            "mcp_github_create_issue",
            {},
            session_key=SessionKey(type="cli", channel_id="default", chat_id="direct"),
        )
    )
    assert "not found" in str(result.result)
