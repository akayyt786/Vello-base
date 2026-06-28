"""
RealtimeConsumer: WebSocket handler for Firebase-style realtime subscriptions.

Protocol (JSON over WebSocket):
  Client → Server:
    {"type": "subscribe",   "requestId": "r1", "path": "users/alice"}
    {"type": "subscribe",   "requestId": "r2", "path": "users", "query": {"where": [["status","==","active"]]}}
    {"type": "unsubscribe", "requestId": "r3", "subscriptionId": "sub_xxx"}
    {"type": "presence.set","requestId": "r4", "path": ".info/connected", "value": true}
    {"type": "ondisconnect.set","requestId":"r5","path":"users/alice","value":{...}}
    {"type": "ping"}

  Server → Client:
    {"type": "subscribed", "requestId": "r1", "subscriptionId": "sub_xxx", "snapshot": {...}, "version": 1}
    {"type": "change",     "subscriptionId": "sub_xxx", "event": "modified|added|removed", "data": {...}}
    {"type": "pong"}
    {"type": "error",      "requestId": "r1", "code": "PERMISSION_DENIED|NOT_FOUND|INVALID", "message": "..."}
"""

import json
import logging
import uuid

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


def _doc_group(project_id: str, collection_path: str, doc_id: str) -> str:
    # project_id is always the first segment — prevents cross-project group collisions.
    safe = lambda s: str(s).replace('/', '__').replace('-', '_')
    return f'p_{safe(project_id)}_d_{safe(collection_path)}_{safe(doc_id)}'


def _col_group(project_id: str, collection_path: str) -> str:
    # project_id is always the first segment — prevents cross-project group collisions.
    safe = lambda s: str(s).replace('/', '__').replace('-', '_')
    return f'p_{safe(project_id)}_c_{safe(collection_path)}'


def _parse_path(path: str):
    parts = [p for p in path.strip('/').split('/') if p]
    if len(parts) >= 2 and len(parts) % 2 == 0:
        doc_id = parts[-1]
        collection_path = '/'.join(parts[:-1])
        return collection_path, doc_id
    elif len(parts) >= 1 and len(parts) % 2 == 1:
        return '/'.join(parts), None
    return None, None


class RealtimeConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.user = self.scope.get('user')
        self.subscriptions = {}

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        ok = await self._check_project_access()
        if not ok:
            await self.close(code=4403)
            return

        await self.accept()
        logger.info(f'WS connect: user={self.user.id} project={self.project_id}')

    async def disconnect(self, close_code):
        # Guard against disconnect firing before connect() initialised subscriptions
        # (e.g. ASGI server error during handshake).
        for sub_id, sub in list(getattr(self, 'subscriptions', {}).items()):
            await self.channel_layer.group_discard(sub['group'], self.channel_name)

        if self.user and self.user.is_authenticated:
            from realtime.presence import remove_presence, fire_on_disconnect
            await database_sync_to_async(remove_presence)(
                self.project_id, str(self.user.id), self.channel_name
            )
            await database_sync_to_async(fire_on_disconnect)(
                self.project_id, str(self.user.id), self.channel_name
            )

        logger.info(f'WS disconnect: user={getattr(self.user, "id", "?")} code={close_code}')

    async def receive_json(self, content, **kwargs):
        msg_type = content.get('type')
        request_id = content.get('requestId', '')

        handlers = {
            'subscribe': self._handle_subscribe,
            'unsubscribe': self._handle_unsubscribe,
            'presence.set': self._handle_presence_set,
            'ondisconnect.set': self._handle_ondisconnect_set,
            'ping': self._handle_ping,
        }

        handler = handlers.get(msg_type)
        if handler is None:
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'INVALID', 'message': f'Unknown type: {msg_type}'})
            return

        try:
            await handler(content)
        except Exception as e:
            logger.exception(f'handler error for {msg_type}')
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'INTERNAL', 'message': str(e)})

    async def _handle_ping(self, content):
        await self.send_json({'type': 'pong'})

    async def _handle_subscribe(self, content):
        request_id = content.get('requestId', '')
        path = content.get('path', '')
        query = content.get('query')

        collection_path, doc_id = _parse_path(path)
        if not collection_path:
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'INVALID', 'message': 'Invalid path'})
            return

        sub_id = f'sub_{uuid.uuid4().hex[:12]}'

        if doc_id:
            group = _doc_group(self.project_id, collection_path, doc_id)
            snapshot = await self._fetch_document(collection_path, doc_id)
        else:
            group = _col_group(self.project_id, collection_path)
            snapshot = await self._fetch_collection(collection_path, query)

        await self.channel_layer.group_add(group, self.channel_name)
        self.subscriptions[sub_id] = {
            'group': group,
            'collection_path': collection_path,
            'doc_id': doc_id,
            'query': query,
        }

        await self.send_json({
            'type': 'subscribed',
            'requestId': request_id,
            'subscriptionId': sub_id,
            'snapshot': snapshot,
        })

    async def _handle_unsubscribe(self, content):
        request_id = content.get('requestId', '')
        sub_id = content.get('subscriptionId', '')

        sub = self.subscriptions.pop(sub_id, None)
        if sub:
            await self.channel_layer.group_discard(sub['group'], self.channel_name)
            await self.send_json({'type': 'unsubscribed', 'requestId': request_id,
                                  'subscriptionId': sub_id})
        else:
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'NOT_FOUND', 'message': 'Subscription not found'})

    async def _handle_presence_set(self, content):
        request_id = content.get('requestId', '')
        value = content.get('value', {})
        from realtime.presence import set_presence
        await database_sync_to_async(set_presence)(
            self.project_id, str(self.user.id), self.channel_name, value
        )
        await self.send_json({'type': 'presence.ack', 'requestId': request_id})

    async def _handle_ondisconnect_set(self, content):
        request_id = content.get('requestId', '')
        path = content.get('path', '')
        value = content.get('value', {})
        collection_path, doc_id = _parse_path(path)
        if not collection_path or not doc_id:
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'INVALID', 'message': 'Path must point to a document'})
            return
        # Authorize: user must have write access to the target document now,
        # before we store a deferred write that fires on disconnect.
        allowed = await self._check_write_access(collection_path, doc_id, value)
        if not allowed:
            await self.send_json({'type': 'error', 'requestId': request_id,
                                  'code': 'PERMISSION_DENIED',
                                  'message': 'Write permission denied for that path'})
            return
        from realtime.presence import register_on_disconnect
        await database_sync_to_async(register_on_disconnect)(
            self.project_id, str(self.user.id), self.channel_name,
            collection_path, doc_id, value
        )
        await self.send_json({'type': 'ondisconnect.ack', 'requestId': request_id})

    async def realtime_event(self, event):
        # Secondary project-scope guard: even though group names already embed
        # project_id (preventing cross-project delivery), we double-check here
        # to defend against any future group-naming regression.
        project_id = event.get('project_id')
        if project_id != self.project_id:
            return

        collection_path = event.get('collection_path')
        doc_id = event.get('doc_id')
        evt_type = event.get('event')
        data = event.get('data')
        version = event.get('version', 0)

        matching_subs = []
        for sub_id, sub in self.subscriptions.items():
            if sub['collection_path'] != collection_path:
                continue
            if sub['doc_id'] and sub['doc_id'] == doc_id:
                matching_subs.append(sub_id)
            elif not sub['doc_id']:
                if self._matches_query(data, sub.get('query')):
                    matching_subs.append(sub_id)

        for sub_id in matching_subs:
            await self.send_json({
                'type': 'change',
                'subscriptionId': sub_id,
                'event': evt_type,
                'data': data,
                'version': version,
                'docId': doc_id,
            })

    def _matches_query(self, data: dict, query: dict) -> bool:
        if not query or not data:
            return True
        for condition in query.get('where', []):
            if len(condition) != 3:
                continue
            field, op, value = condition
            field_val = data.get(field)
            if op == '==' and field_val != value:
                return False
            elif op == '!=' and field_val == value:
                return False
            elif op == '>' and not (field_val is not None and field_val > value):
                return False
            elif op == '>=' and not (field_val is not None and field_val >= value):
                return False
            elif op == '<' and not (field_val is not None and field_val < value):
                return False
            elif op == '<=' and not (field_val is not None and field_val <= value):
                return False
        return True

    @database_sync_to_async
    def _check_project_access(self) -> bool:
        from core.models import Project, ProjectMembership
        try:
            project = Project.objects.get(id=self.project_id, is_active=True)
            return ProjectMembership.objects.filter(
                project=project, user=self.user
            ).exists()
        except Project.DoesNotExist:
            return False

    @database_sync_to_async
    def _check_write_access(self, collection_path: str, doc_id: str, data: dict) -> bool:
        """Verify user can write to this document path via project membership role."""
        from core.models import Project, ProjectMembership
        try:
            project = Project.objects.get(id=self.project_id, is_active=True)
            membership = ProjectMembership.objects.get(project=project, user=self.user)
            return membership.role in ('owner', 'editor')
        except (Project.DoesNotExist, ProjectMembership.DoesNotExist):
            return False

    @database_sync_to_async
    def _fetch_document(self, collection_path: str, doc_id: str) -> dict:
        from data.models import Document
        from core.models import Project
        try:
            project = Project.objects.get(id=self.project_id)
            doc = Document.objects.get(
                project=project,
                collection_path=collection_path,
                doc_id=doc_id,
            )
            return {
                'doc_id': doc.doc_id,
                'collection_path': doc.collection_path,
                'data': doc.data,
                'version': doc.v,
                'created_at': doc.created_at.isoformat(),
                'updated_at': doc.updated_at.isoformat(),
            }
        except Document.DoesNotExist:
            return None

    @database_sync_to_async
    def _fetch_collection(self, collection_path: str, query: dict = None) -> list:
        from data.models import Document
        from core.models import Project
        try:
            project = Project.objects.get(id=self.project_id)
            qs = Document.objects.filter(
                project=project,
                collection_path=collection_path,
            ).order_by('-updated_at')[:100]

            docs = []
            for doc in qs:
                if query and not self._matches_query_sync(doc.data, query):
                    continue
                docs.append({
                    'doc_id': doc.doc_id,
                    'collection_path': doc.collection_path,
                    'data': doc.data,
                    'version': doc.v,
                    'created_at': doc.created_at.isoformat(),
                    'updated_at': doc.updated_at.isoformat(),
                })
            return docs
        except Project.DoesNotExist:
            return []

    def _matches_query_sync(self, data: dict, query: dict) -> bool:
        return self._matches_query(data, query)
