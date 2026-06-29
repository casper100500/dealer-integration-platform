from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


@extend_schema(tags=["Auth"])
class AuthTokenObtainPairView(TokenObtainPairView):
    """Issue JWT access and refresh tokens."""


@extend_schema(tags=["Auth"])
class AuthTokenRefreshView(TokenRefreshView):
    """Refresh a JWT access token."""


@extend_schema(tags=["Auth"])
class AuthTokenVerifyView(TokenVerifyView):
    """Verify a JWT token."""


def health_check(request: HttpRequest) -> JsonResponse:
    """Return application health status."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api-auth/",
        include("rest_framework.urls", namespace="rest_framework"),
    ),
    path(
        "api/v1/auth/token/",
        AuthTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        AuthTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "api/v1/auth/token/verify/",
        AuthTokenVerifyView.as_view(),
        name="token_verify",
    ),
    path("api/v1/", include("dealer_platform.inventory.urls")),
    path(
        "swagger/v1/swagger.json",
        SpectacularJSONAPIView.as_view(),
        name="schema",
    ),
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("health/", health_check),
]
