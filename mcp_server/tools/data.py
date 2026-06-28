"""MCP tools for the Data API — Firestore-like NoSQL collections and documents."""

import json
from typing import Optional
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def data_list_collections(project_id: str) -> str:
        """List all collections in a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/collections/"))

    @mcp.tool()
    async def data_create_collection(project_id: str, name: str) -> str:
        """Create a new collection in a project."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/collections/",
            json={"name": name},
        ))

    @mcp.tool()
    async def data_list_documents(
        project_id: str,
        collection: str,
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """List documents in a collection. collection can include subcollection path."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/collections/{collection}/docs/",
            params={"limit": limit, "offset": offset},
        ))

    @mcp.tool()
    async def data_get_document(project_id: str, collection: str, doc_id: str) -> str:
        """Get a single document by its ID from a collection."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/collections/{collection}/docs/{doc_id}/",
        ))

    @mcp.tool()
    async def data_create_document(
        project_id: str,
        collection: str,
        data_json: str,
        doc_id: str = "",
    ) -> str:
        """Create a document in a collection. data_json is a JSON string of field values."""
        body: dict = {"data": json.loads(data_json)}
        if doc_id:
            body["id"] = doc_id
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/collections/{collection}/docs/",
            json=body,
        ))

    @mcp.tool()
    async def data_update_document(
        project_id: str,
        collection: str,
        doc_id: str,
        data_json: str,
        merge: bool = True,
    ) -> str:
        """Update a document. data_json is a JSON string. merge=True for partial update."""
        body = {"data": json.loads(data_json)}
        method = _c.patch if merge else _c.put
        return json.dumps(await method(
            f"/api/projects/{project_id}/collections/{collection}/docs/{doc_id}/",
            json=body,
        ))

    @mcp.tool()
    async def data_delete_document(project_id: str, collection: str, doc_id: str) -> str:
        """Delete a document from a collection."""
        return json.dumps(await _c.delete(
            f"/api/projects/{project_id}/collections/{collection}/docs/{doc_id}/",
        ))

    @mcp.tool()
    async def data_query(
        project_id: str,
        collection: str,
        filters_json: str = "[]",
        order_by: str = "",
        limit: int = 20,
    ) -> str:
        """Query documents with filters. filters_json: JSON array of [field, op, value] triples."""
        body: dict = {
            "collection": collection,
            "filters": json.loads(filters_json),
            "limit": limit,
        }
        if order_by:
            body["order_by"] = order_by
        return json.dumps(await _c.post(f"/api/v1/data/query/", json=body))

    @mcp.tool()
    async def data_write_batch(project_id: str, writes_json: str) -> str:
        """Batch write multiple documents atomically. writes_json is a JSON array of write ops."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/transaction/",
            json={"writes": json.loads(writes_json)},
        ))

    @mcp.tool()
    async def data_list_documents_v1(
        project_id: str,
        limit: int = 20,
    ) -> str:
        """List documents via v1 API endpoint."""
        return json.dumps(await _c.get(
            f"/api/v1/projects/{project_id}/documents/",
            params={"limit": limit},
        ))
