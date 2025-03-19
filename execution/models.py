from django.db import models
import uuid
from users.models import User
from projects.models import Project

class ExecutionResult(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='executions')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='executions')
    command = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Execution {self.id} - {self.status}"