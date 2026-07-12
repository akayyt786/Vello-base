"""OwnFirebase Base Client with HTTP utilities."""

from typing import Any, Dict, Optional
import json
import requests
from .config import OwnFirebaseConfig
from .errors import APIError

class OwnFirebaseClient:
    """Base client with shared HTTP functionality."""

    def __init__(self, config: OwnFirebaseConfig) -> None:
        self.base_url = config.base_url
        self.project_id = config.project_id
        self.access_token = config.access_token

    def set_access_token(self, token: str) -> None:
        self.access_token = token

    def set_project_id(self, project_id: str) -> None:
        self.project_id = project_id

    def project_url(self, path: str) -> str:
        if not self.project_id:
            raise ValueError('project_id is required for this operation')
        return f"{self.base_url}/api/projects/{self.project_id}/{path}"

    def request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        no_auth: bool = False,
        query_params: Optional[Dict[str, str]] = None,
    ) -> Any:
        headers: Dict[str, str] = {'Content-Type': 'application/json'}
        if not no_auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        params = query_params or {}
        
        try:
            response = requests.request(
                method=method, url=url, json=json_data,
                headers=headers, params=params, timeout=30
            )
        except requests.exceptions.RequestException as e:
            raise APIError(status=0, message="Request failed", detail=str(e)) from e

        if not response.ok:
            try:
                detail = response.json()
            except (json.JSONDecodeError, ValueError):
                detail = response.text
            raise APIError(
                status=response.status_code,
                message=response.reason or 'Unknown Error',
                detail=detail
            )

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return response.text
