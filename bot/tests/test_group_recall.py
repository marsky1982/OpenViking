# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""bot.group_recall injects per-asker group memory for Feishu private chats only."""

import asyncio
import json

import httpx
from vikingbot.agent import group_recall
from vikingbot.agent.context import ContextBuilder
from vikingbot.config.schema import Config, SessionKey

FEISHU = SessionKey(type="feishu", channel_id="cli_app", chat_id="oc_p2p")
URL = "http://127.0.0.1:8000/internal/vikingbot/group-recall"


def _config(**overrides):
    return Config(group_recall={"enabled": True, "url": URL, **overrides})


def test_applies_only_to_enabled_feishu_private_chats():
    config = _config()
    assert group_recall.applies(config, FEISHU, "on_1", is_group_chat=False)
    assert not group_recall.applies(Config(), FEISHU, "on_1", is_group_chat=False)
    assert not group_recall.applies(config, FEISHU, "on_1", is_group_chat=True)
    assert not group_recall.applies(config, FEISHU, "ou_open_id_is_app_scoped", is_group_chat=False)
    assert not group_recall.applies(config, FEISHU, None, is_group_chat=False)
    cli = SessionKey(type="cli", channel_id="default", chat_id="direct")
    assert not group_recall.applies(config, cli, "on_1", is_group_chat=False)


def test_fetch_sends_open_id_and_token_and_truncates(monkeypatch):
    monkeypatch.setenv("VIKINGBOT_GROUP_RECALL_TOKEN", "svc")
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"context": "群A：周二发布" * 10, "groups": 1})

    text = asyncio.run(
        group_recall.fetch_group_memory(
            _config(max_chars=8), "on_1", "发布时间", transport=httpx.MockTransport(handler)
        )
    )
    assert seen == {"auth": "Bearer svc", "body": {"union_id": "on_1", "query": "发布时间"}}
    assert text == "群A：周二发布群"


def test_fetch_degrades_to_empty(monkeypatch):
    monkeypatch.delenv("VIKINGBOT_GROUP_RECALL_TOKEN", raising=False)
    calls = []
    transport = httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200, json={}))
    assert (
        asyncio.run(group_recall.fetch_group_memory(_config(), "on_1", "q", transport=transport))
        == ""
    )
    assert not calls  # no token: no request

    monkeypatch.setenv("VIKINGBOT_GROUP_RECALL_TOKEN", "svc")
    for response in (httpx.Response(401), httpx.Response(200, content=b"not json")):
        transport = httpx.MockTransport(lambda r, resp=response: resp)
        assert (
            asyncio.run(
                group_recall.fetch_group_memory(_config(), "on_1", "q", transport=transport)
            )
            == ""
        )

    def boom(request):
        raise httpx.ConnectTimeout("down")

    assert (
        asyncio.run(
            group_recall.fetch_group_memory(
                _config(), "on_1", "q", transport=httpx.MockTransport(boom)
            )
        )
        == ""
    )


def test_context_includes_group_memory_section(tmp_path, monkeypatch):
    async def fake_fetch(config, sender_id, query, transport=None):
        assert sender_id == "on_1" and query == "发布时间"
        return "群A：周二发布"

    monkeypatch.setattr(group_recall, "fetch_group_memory", fake_fetch)
    builder = ContextBuilder(
        workspace=tmp_path, sender_id="ou_1", sender_union_id="on_1", config=_config()
    )
    text = asyncio.run(
        builder._build_user_memory(FEISHU, "发布时间", "ou_1", ov_tools_enable=False)
    )
    assert "## Group Memory" in text and "群A：周二发布" in text

    group = ContextBuilder(
        workspace=tmp_path,
        sender_id="ou_1",
        sender_union_id="on_1",
        is_group_chat=True,
        config=_config(),
    )
    text = asyncio.run(group._build_user_memory(FEISHU, "发布时间", "ou_1", ov_tools_enable=False))
    assert "## Group Memory" not in text
