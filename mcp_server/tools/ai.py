"""MCP tools for AI Proxy (chat completions, embeddings, usage)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def ai_list_providers(project_id: str) -> str:
        """List configured AI provider connections for a project (OpenAI, Anthropic, etc.)."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/ai/providers/"))

    @mcp.tool()
    async def ai_add_provider(
        project_id: str,
        provider: str,
        api_key: str,
        model: str = "",
    ) -> str:
        """Add an AI provider API key. provider: openai|anthropic|google. model: default model."""
        body: dict = {"provider": provider, "api_key": api_key}
        if model:
            body["model"] = model
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/ai/providers/",
            json=body,
        ))

    @mcp.tool()
    async def ai_chat(
        project_id: str,
        messages_json: str,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat completion request via the AI proxy. messages_json: JSON array of {role, content}."""
        body: dict = {
            "messages": json.loads(messages_json),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model:
            body["model"] = model
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/ai/chat/",
            json=body,
        ))

    @mcp.tool()
    async def ai_embed(project_id: str, text: str, model: str = "") -> str:
        """Generate embeddings for text using the configured AI provider."""
        body: dict = {"text": text}
        if model:
            body["model"] = model
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/ai/embeddings/",
            json=body,
        ))

    @mcp.tool()
    async def ai_get_usage(project_id: str) -> str:
        """Get AI API usage statistics (tokens, requests, cost estimates) for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/ai/usage/"))
