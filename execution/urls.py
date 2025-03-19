from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExecutionResultViewSet

router = DefaultRouter()
router.register(r'', ExecutionResultViewSet, basename='executions')

urlpatterns = [
    path('', include(router.urls)),
]