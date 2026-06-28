import logging
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Project, ProjectMembership
from ai.models import AIProviderConfig
from ai.encryption import decrypt_api_key
from ai.services import call_anthropic, call_google
from .models import VectorCollection, VectorDocument
from .serializers import (
    VectorCollectionSerializer, VectorDocumentSerializer,
    IngestDocumentSerializer, SearchSerializer, RAGQuerySerializer,
)
from .services import embed_texts, similarity_search, build_rag_prompt

logger = logging.getLogger(__name__)


def _get_project_and_membership(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


class VectorCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = VectorCollectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'])
        return VectorCollection.objects.filter(project=project)

    def perform_create(self, serializer):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        serializer.save(project=project)

    def perform_update(self, serializer):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        serializer.save()

    def perform_destroy(self, instance):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='ingest')
    def ingest(self, request, pk=None, project_id=None):
        project, _ = _get_project_and_membership(request, project_id, require_editor=True)
        collection = get_object_or_404(VectorCollection, pk=pk, project=project)
        ser = IngestDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        docs_data = ser.validated_data['documents']
        do_embed = ser.validated_data['embed']

        embeddings = None
        if do_embed:
            provider_cfg = AIProviderConfig.objects.filter(project=project, provider='openai', is_active=True).first()
            if not provider_cfg:
                return Response(
                    {'error': 'No active OpenAI provider configured. Add one to enable auto-embedding.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                texts = [d.get('content', '') for d in docs_data]
                api_key = decrypt_api_key(provider_cfg.api_key_encrypted)
                embeddings = embed_texts(texts, api_key, collection.embedding_model)
            except Exception as exc:
                logger.exception('Embedding failed during ingest')
                return Response({'error': 'Embedding service error.'}, status=status.HTTP_502_BAD_GATEWAY)

        created = []
        for i, doc_data in enumerate(docs_data):
            doc = VectorDocument.objects.create(
                collection=collection,
                external_id=doc_data.get('external_id', ''),
                content=doc_data.get('content', ''),
                metadata=doc_data.get('metadata', {}),
                embedding=embeddings[i] if embeddings else None,
            )
            created.append(str(doc.id))

        return Response({'created': len(created), 'ids': created}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='search')
    def search(self, request, pk=None, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        collection = get_object_or_404(VectorCollection, pk=pk, project=project)
        ser = SearchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        provider_cfg = AIProviderConfig.objects.filter(project=project, provider='openai', is_active=True).first()
        if not provider_cfg:
            return Response(
                {'error': 'No active OpenAI provider configured for embeddings.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            api_key = decrypt_api_key(provider_cfg.api_key_encrypted)
            query_embeddings = embed_texts([d['query']], api_key, collection.embedding_model)
            query_embedding = query_embeddings[0]
        except Exception as exc:
            logger.exception('Search embedding error')
            return Response({'error': 'Embedding service error.'}, status=status.HTTP_502_BAD_GATEWAY)

        results = similarity_search(collection, query_embedding, top_k=d['top_k'], threshold=d['threshold'])
        response_data = []
        for doc, score in results:
            item = {
                'id': str(doc.id),
                'content': doc.content,
                'score': round(score, 4),
                'external_id': doc.external_id,
            }
            if d['include_metadata']:
                item['metadata'] = doc.metadata
            response_data.append(item)
        return Response({'results': response_data, 'count': len(response_data)})

    @action(detail=True, methods=['post'], url_path='query')
    def rag_query(self, request, pk=None, project_id=None):
        """Full RAG: embed query -> search -> generate answer with context."""
        project, _ = _get_project_and_membership(request, project_id)
        collection = get_object_or_404(VectorCollection, pk=pk, project=project)
        ser = RAGQuerySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        openai_cfg = AIProviderConfig.objects.filter(project=project, provider='openai', is_active=True).first()
        if not openai_cfg:
            return Response(
                {'error': 'OpenAI provider required for RAG embeddings.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ai_cfg = AIProviderConfig.objects.filter(project=project, provider=d['provider'], is_active=True).first()
        if not ai_cfg:
            return Response(
                {'error': f"No active {d['provider']} provider configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            openai_key = decrypt_api_key(openai_cfg.api_key_encrypted)
            query_embedding = embed_texts([d['query']], openai_key, collection.embedding_model)[0]
        except Exception as exc:
            logger.exception('RAG embedding error')
            return Response({'error': 'Embedding service error.'}, status=status.HTTP_502_BAD_GATEWAY)

        docs_with_scores = similarity_search(collection, query_embedding, top_k=d['top_k'])
        if not docs_with_scores:
            return Response({'answer': 'No relevant documents found.', 'sources': []})

        system, messages = build_rag_prompt(d['query'], docs_with_scores, d.get('system', ''))
        ai_key = decrypt_api_key(ai_cfg.api_key_encrypted)
        try:
            if d['provider'] == 'anthropic':
                result = call_anthropic(ai_key, d['model'], messages, d['max_tokens'], 0.3, system)
            else:
                result = call_google(ai_key, d['model'], messages, d['max_tokens'], 0.3, system)
        except Exception as exc:
            logger.exception('RAG generation error')
            return Response({'error': 'Upstream provider error.'}, status=status.HTTP_502_BAD_GATEWAY)

        sources = [
            {'id': str(doc.id), 'score': round(score, 4), 'external_id': doc.external_id}
            for doc, score in docs_with_scores
        ]
        return Response({'answer': result['content'], 'sources': sources, 'usage': result['usage']})
