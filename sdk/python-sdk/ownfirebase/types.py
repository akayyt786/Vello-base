"""OwnFirebase SDK Type Definitions."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

@dataclass
class AuthTokens:
    access: str
    refresh: str
    user_id: str
    email: Optional[str] = None

@dataclass
class User:
    id: str
    email: str
    username: str
    first_name: str
    last_name: str
    is_active: bool

@dataclass
class Project:
    id: str
    name: str
    slug: str
    description: str
    created_at: str
    updated_at: str

@dataclass
class DataDocument:
    id: str
    collection: str
    data: Dict[str, Any]
    created_at: str
    updated_at: str

@dataclass
class DataCollection:
    id: str
    name: str
    document_count: int

@dataclass
class PaginatedResponse:
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[Any] = field(default_factory=list)

@dataclass
class WriteBatchOperation:
    op: Literal['set', 'update', 'delete']
    collection: str
    doc_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class WriteBatchResult:
    written: int
    errors: List[Any] = field(default_factory=list)

# Additional type definitions continue...
# (AnalyticsEvent, PerformanceTrace, CrashReport, etc.)
