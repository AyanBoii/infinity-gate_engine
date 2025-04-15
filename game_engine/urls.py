from django.urls import path
from . import views

app_name = 'game_engine'

urlpatterns = [
    # API endpoints for React frontend
    path('api/game/new-session/', views.create_game_session, name='create_game_session'),
    path('api/game/scene/<str:session_id>/', views.get_game_scene, name='get_game_scene'),
    path('api/game/choice/<str:session_id>/', views.make_choice, name='make_choice'),
] 