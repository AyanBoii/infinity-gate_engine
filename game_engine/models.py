from django.db import models
import uuid
import json

class GameSession(models.Model):
    """Model to store game session data"""
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    game_state = models.JSONField()
    
    def __str__(self):
        return f"GameSession {self.session_id}" 