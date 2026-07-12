"""OwnFirebase Python SDK - Self-hosted Firebase alternative."""

__version__ = '0.5.0'

from .config import OwnFirebaseConfig
from .errors import APIError
from .auth import AuthSDK
from .data import DataSDK
from .storage import StorageSDK
from .functions import FunctionsSDK
from .realtime import RealtimeSDK
from .analytics import AnalyticsSDK
from .remote_config import RemoteConfigSDK
from .crashlytics import CrashlyticsSDK
from .abtesting import ABTestingSDK
from .push import PushSDK
from .projects import ProjectsSDK
from .appcheck import AppCheckSDK

class OwnFirebase:
    """Main SDK class with all services."""
    
    def __init__(self, config: OwnFirebaseConfig) -> None:
        self.auth = AuthSDK(config)
        self.data = DataSDK(config)
        self.storage = StorageSDK(config)
        self.functions = FunctionsSDK(config)
        self.realtime = RealtimeSDK(config)
        self.analytics = AnalyticsSDK(config)
        self.remote_config = RemoteConfigSDK(config)
        self.crashlytics = CrashlyticsSDK(config)
        self.abtesting = ABTestingSDK(config)
        self.push = PushSDK(config)
        self.projects = ProjectsSDK(config)
        self.appcheck = AppCheckSDK(config)
        
        self._services = [
            self.auth, self.data, self.storage, self.functions, self.realtime,
            self.analytics, self.remote_config, self.crashlytics, self.abtesting,
            self.push, self.projects, self.appcheck
        ]
    
    def set_access_token(self, token: str) -> None:
        """Propagate JWT token to all services."""
        for svc in self._services:
            svc.set_access_token(token)
    
    def set_project_id(self, project_id: str) -> None:
        """Propagate project ID to all services."""
        for svc in self._services:
            svc.set_project_id(project_id)

def init_ownfirebase(config: OwnFirebaseConfig) -> OwnFirebase:
    """Factory function to initialize SDK."""
    return OwnFirebase(config)

__all__ = [
    'OwnFirebase', 'OwnFirebaseConfig', 'APIError',
    'AuthSDK', 'DataSDK', 'StorageSDK', 'FunctionsSDK',
    'RealtimeSDK', 'AnalyticsSDK', 'RemoteConfigSDK',
    'CrashlyticsSDK', 'ABTestingSDK', 'PushSDK',
    'ProjectsSDK', 'AppCheckSDK', 'init_ownfirebase'
]
