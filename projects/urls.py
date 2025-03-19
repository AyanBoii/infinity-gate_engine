from django.urls import path, include
from rest_framework_nested import routers
from .views import ProjectViewSet, FileViewSet

router = routers.SimpleRouter()
router.register(r'', ProjectViewSet, basename='projects')

files_router = routers.NestedSimpleRouter(router, r'', lookup='project')
files_router.register(r'files', FileViewSet, basename='project-files')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(files_router.urls)),
]