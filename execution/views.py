from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ExecutionResult
from .serializers import ExecutionResultSerializer
from .services import CodeExecutionService
from projects.models import Project

class ExecutionResultViewSet(viewsets.ModelViewSet):
    serializer_class = ExecutionResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return ExecutionResult.objects.filter(project_id=project_id)
        return ExecutionResult.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project_id')
        command = request.data.get('command')
        
        if not project_id or not command:
            return Response(
                {'error': 'Both project_id and command are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has access to the project
        project = get_object_or_404(Project, id=project_id)
        if project.owner != request.user and not project.collaborators.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have access to this project'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Execute code
        service = CodeExecutionService()
        execution = service.execute_code(project_id, request.user.id, command)
        
        serializer = self.get_serializer(execution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)