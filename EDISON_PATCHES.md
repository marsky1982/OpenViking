# Edison patches on top of OpenViking v0.5.0

Branch `edison/v0.5.0` in `marsky1982/OpenViking` carries the VikingBot changes needed to run
VikingBot as the Edison private-chat bot (Linear MAR-67). Every patch keeps upstream behaviour
when its setting is left at the default, so the branch can be rebased onto later tags.

## Install

Building this repository needs cmake and maturin. For VikingBot only the `bot/vikingbot`
package is patched, so install the released wheel and put the patched package first on the path:

```bash
uv pip install "openviking[bot,bot-feishu]==0.5.0"
PYTHONPATH=<checkout>/bot vikingbot gateway
```

The wheel version must match the tag the branch is based on.

## Patches

| Patch | Setting | Linear |
|---|---|---|
| Global tool deny-list: tools named here are never registered for the agent, subagents or MCP wrappers | `bot.tools.disabled_tools: list[str]` (default `[]`) | MAR-69 |
| Per-asker group memory: for Feishu private chats, POST `{open_id, query}` to a trusted service (Bearer token from `token_env`) and inject the returned context as a "Group Memory" section; failures and timeouts inject nothing | `bot.group_recall.{enabled,url,token_env,timeout_seconds,max_chars}` (default off) | MAR-71 |

## Tests

```bash
cd bot
PYTHONPATH=. python -m pytest -q tests/test_disabled_tools.py tests/test_group_recall.py
```
