"""
URL configuration for Data API endpoints.
"""

from django.urls import path
from data.views import CollectionViewSet, DocumentViewSet, TransactionViewSet

# Collection endpoints
collection_list = CollectionViewSet.as_view({'get': 'list', 'post': 'create'})

# Document endpoints
doc_list = DocumentViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
doc_detail = DocumentViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

# Transaction endpoints
transaction_write = TransactionViewSet.as_view({'post': 'write_batch'})

urlpatterns = [
    # Collections
    path(
        'projects/<uuid:project_id>/collections/',
        collection_list,
        name='collection-list'
    ),

    # Documents
    path(
        'projects/<uuid:project_id>/collections/<str:collection>/docs/',
        doc_list,
        name='document-list'
    ),
    path(
        'projects/<uuid:project_id>/collections/<str:collection>/docs/<str:doc_id>/',
        doc_detail,
        name='document-detail'
    ),

    # Transactions
    path(
        'projects/<uuid:project_id>/transaction/',
        transaction_write,
        name='transaction-write'
    ),
]
