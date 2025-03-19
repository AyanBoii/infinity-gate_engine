from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('world/', views.world, name='world'),
    path('character/', views.character, name='character'),
    path('game/', views.game, name='game'),
] 