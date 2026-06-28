from django.urls import path
from .views import GoogleSignInView, GitHubSignInView, LinkedAccountsView

app_name = "social_auth"

urlpatterns = [
    path("google/", GoogleSignInView.as_view(), name="social-google"),
    path("github/", GitHubSignInView.as_view(), name="social-github"),
    path("linked/", LinkedAccountsView.as_view(), name="social-linked"),
    path("linked/<uuid:pk>/", LinkedAccountsView.as_view(), name="social-linked-delete"),
]
