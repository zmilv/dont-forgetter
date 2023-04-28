from django.contrib import admin
from django.urls import path
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
urlpatterns = router.urls

urlpatterns += [
    path('admin/', admin.site.urls),
    path('event/', views.EventsAPIView.as_view()),
    path('event/<int:id>/', views.EventsAPIDetailView.as_view()),
]
