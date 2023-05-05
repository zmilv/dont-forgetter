from django.contrib import admin
from django.urls import path
from core import views
from rest_framework import routers

router = routers.DefaultRouter()
urlpatterns = router.urls

urlpatterns += [
    path('admin/', admin.site.urls),
    path('event/', views.EventAPIView.as_view()),
    path('event/<int:id>/', views.EventAPIDetailView.as_view()),
    path('note/', views.NoteAPIView.as_view()),
    path('note/<int:id>/', views.NoteAPIDetailView.as_view()),
]
