import json
import logging
import math

from django.conf import settings

logger = logging.getLogger(__name__)


def cosine_similarity(a, b):
    """Cosine similarity between two float lists. Used for SQLite fallback."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_texts(texts, api_key, model='text-embedding-3-small'):
    """
    Get embeddings from OpenAI. Returns list of float lists.
    Raises on API error.
    """
    import requests
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    resp = requests.post(
        'https://api.openai.com/v1/embeddings',
        json={'input': texts, 'model': model},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [item['embedding'] for item in data['data']]


def similarity_search(collection, query_embedding, top_k=5, threshold=0.0):
    """
    Find top_k most similar documents in collection.
    Uses Python cosine similarity (works on all DBs).
    For production Postgres, migrate embedding to vector column and use pgvector operators.
    Returns list of (document, score) tuples sorted by score desc.
    """
    from .models import VectorDocument
    docs = VectorDocument.objects.filter(collection=collection).exclude(embedding=None)
    scored = []
    for doc in docs:
        emb = doc.embedding
        if not isinstance(emb, list):
            try:
                emb = json.loads(emb)
            except Exception:
                continue
        score = cosine_similarity(query_embedding, emb)
        if score >= threshold:
            scored.append((doc, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def build_rag_prompt(query, docs_with_scores, system_prefix=""):
    """Build a prompt that includes retrieved context for RAG."""
    context_parts = []
    for i, (doc, score) in enumerate(docs_with_scores, 1):
        context_parts.append(f"[{i}] (score={score:.3f}) {doc.content}")
    context = "\n\n".join(context_parts)
    system = f"{system_prefix}\n\nContext from knowledge base:\n{context}".strip()
    messages = [{"role": "user", "content": query}]
    return system, messages
