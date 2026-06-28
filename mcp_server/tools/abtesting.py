"""MCP tools for A/B Testing experiments."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def abtesting_list_experiments(project_id: str) -> str:
        """List all A/B testing experiments for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/abtesting/experiments/"))

    @mcp.tool()
    async def abtesting_create_experiment(
        project_id: str,
        name: str,
        description: str = "",
        traffic_percentage: float = 100.0,
    ) -> str:
        """Create a new A/B testing experiment."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/abtesting/experiments/",
            json={
                "name": name,
                "description": description,
                "traffic_percentage": traffic_percentage,
            },
        ))

    @mcp.tool()
    async def abtesting_get_experiment(project_id: str, experiment_id: str) -> str:
        """Get details of a specific A/B testing experiment including variants."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/abtesting/experiments/{experiment_id}/",
        ))

    @mcp.tool()
    async def abtesting_update_experiment(
        project_id: str,
        experiment_id: str,
        status: str = "",
        traffic_percentage: float | None = None,
    ) -> str:
        """Update an experiment. status: draft|running|paused|completed."""
        body: dict = {}
        if status:
            body["status"] = status
        if traffic_percentage is not None:
            body["traffic_percentage"] = traffic_percentage
        return json.dumps(await _c.patch(
            f"/api/projects/{project_id}/abtesting/experiments/{experiment_id}/",
            json=body,
        ))

    @mcp.tool()
    async def abtesting_delete_experiment(project_id: str, experiment_id: str) -> str:
        """Delete an A/B testing experiment."""
        return json.dumps(await _c.delete(
            f"/api/projects/{project_id}/abtesting/experiments/{experiment_id}/",
        ))

    @mcp.tool()
    async def abtesting_list_variants(project_id: str, experiment_id: str) -> str:
        """List variants (arms) of an A/B testing experiment."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/config/experiments/{experiment_id}/variants/",
        ))

    @mcp.tool()
    async def abtesting_create_variant(
        project_id: str,
        experiment_id: str,
        name: str,
        weight: float = 50.0,
        config_json: str = "{}",
    ) -> str:
        """Add a variant to an experiment. weight is traffic allocation percentage."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/config/experiments/{experiment_id}/variants/",
            json={"name": name, "weight": weight, "config": json.loads(config_json)},
        ))
