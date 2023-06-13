from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as swagger_get_schema_view

from core import views

router = routers.DefaultRouter()
urlpatterns = router.urls

schema_view = swagger_get_schema_view(
    openapi.Info(
        title="dont-forgetter API",
        default_version="1.0.0",
        description="Documentation for the REST API"
    ),
    public=True,
)

urlpatterns += [
    path("docs/", schema_view.with_ui("swagger", cache_timeout=0), name="docs"),
    path("admin/", admin.site.urls),
    path("event/", views.EventAPIView.as_view()),
    path("event/<int:id>/", views.EventAPIDetailView.as_view()),
    path("note/", views.NoteAPIView.as_view()),
    path("note/<int:id>/", views.NoteAPIDetailView.as_view()),
    path("accounts/", include("rest_framework.urls")),
    path("", include("users.urls", namespace="users")),
]
