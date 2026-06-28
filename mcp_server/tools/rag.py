"""MCP tools for RAG / Vector Search (pgvector-backed semantic search)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def rag_list_collections(project_id: str) -> str:
        """List all vector collections for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/rag/collections/"))

    @mcp.tool()
    async def rag_create_collection(
        project_id: str,
        name: str,
        description: str = "",
        embedding_model: str = "text-embedding-ada-002",
    ) -> str:
        """Create a new vector collection for document storage and semantic search."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/rag/collections/",
            json={"name": name, "description": description, "embedding_model": embedding_model},
        ))

    @mcp.tool()
    async def rag_add_document(
        project_id: str,
        collection_id: str,
        text: str,
        metadata_json: str = "{}",
    ) -> str:
        """Add a document to a vector collection. Text is embedded automatically."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/rag/collections/{collection_id}/documents/",
            json={"text": text, "metadata": json.loads(metadata_json)},
        ))

    @mcp.tool()
    async def rag_search(
        project_id: str,
        collection_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> str:
        """Semantic search in a vector collection. Returns top-k most similar documents."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/rag/collections/{collection_id}/search/",
            json={"query": query, "limit": limit, "threshold": threshold},
        ))

    @mcp.tool()
    async def rag_delete_document(project_id: str, collection_id: str, doc_id: str) -> str:
        """Delete a document from a vector collection."""
        return json.dumps(await _c.delete(
            f"/api/projects/{project_id}/rag/collections/{collection_id}/documents/{doc_id}/",
        ))
