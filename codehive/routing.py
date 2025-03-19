from django.urls import path
from projects.consumers import ProjectConsumer
from users.consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/projects/<str:project_id>/', ProjectConsumer.as_asgi()),
    path('ws/notifications/<str:user_id>/', NotificationConsumer.as_asgi()),
]