from django.urls import path
from .views import GoogleSignInView, GitHubSignInView, AppleSignInView, LinkedAccountsView

app_name = "social_auth"

urlpatterns = [
    path("google/", GoogleSignInView.as_view(), name="social-google"),
    path("github/", GitHubSignInView.as_view(), name="social-github"),
    path("apple/", AppleSignInView.as_view(), name="social-apple"),
    path("linked/", LinkedAccountsView.as_view(), name="social-linked"),
    path("linked/<uuid:pk>/", LinkedAccountsView.as_view(), name="social-linked-delete"),
]
