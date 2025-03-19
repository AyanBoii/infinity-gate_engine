from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import Project, ProjectCollaborator, File, FileVersion
from .serializers import ProjectSerializer, ProjectCollaboratorSerializer, FileSerializer, FileVersionSerializer
from users.models import Notification, User

class IsProjectOwnerOrCollaborator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Check if user is the project owner
        if obj.owner == request.user:
            return True
        
        # Check if user is a collaborator with appropriate role
        if view.action in ['retrieve', 'list']:
            return obj.collaborators.filter(id=request.user.id).exists()
        
        # For update, partial_update, destroy, require admin or editor role
        return obj.projectcollaborator_set.filter(
            user=request.user, 
            role__in=['admin', 'editor']
        ).exists()

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrCollaborator]
    
    def get_queryset(self):
        user = self.request.user
        # Return projects where user is owner or collaborator
        return Project.objects.filter(
            Q(owner=user) | Q(collaborators=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def add_collaborator(self, request, pk=None):
        project = self.get_object()
        
        # Only owner or admin can add collaborators
        if project.owner != request.user and not project.projectcollaborator_set.filter(
            user=request.user, role='admin'
        ).exists():
            return Response(
                {'error': 'Only project owner or admin can add collaborators'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ProjectCollaboratorSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data.pop('user_id')
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create or update collaborator
            collaborator, created = ProjectCollaborator.objects.update_or_create(
                project=project,
                user=user,
                defaults={'role': serializer.validated_data.get('role', 'viewer')}
            )
            
            # Create notification for the added user
            notification = Notification.objects.create(
                user=user,
                message=f"You have been added to project '{project.name}' as a {collaborator.role}"
            )
            
            # Send notification via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'notification',
                    'notification': {
                        'id': str(notification.id),
                        'message': notification.message,
                        'read': notification.read,
                        'created_at': notification.created_at.isoformat()
                    }
                }
            )
            
            return Response(
                ProjectCollaboratorSerializer(collaborator).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_collaborator(self, request, pk=None):
        project = self.get_object()
        user_id = request.query_params.get('user_id')
        
        # Only owner or admin can remove collaborators
        if project.owner != request.user and not project.projectcollaborator_set.filter(
            user=request.user, role='admin'
        ).exists():
            return Response(
                {'error': 'Only project owner or admin can remove collaborators'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            collaborator = ProjectCollaborator.objects.get(project=project, user_id=user_id)
            collaborator.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProjectCollaborator.DoesNotExist:
            return Response(
                {'error': 'Collaborator not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_pk')
        return File.objects.filter(project_id=project_id)
    
    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, id=project_id)
        
        # Check if user has permission to create files
        if project.owner != self.request.user and not project.projectcollaborator_set.filter(
            user=self.request.user, role__in=['admin', 'editor']
        ).exists():
            self.permission_denied(self.request)
        
        serializer.save(project=project, created_by=self.request.user)
        
        # Create initial version
        FileVersion.objects.create(
            file=serializer.instance,
            content=serializer.validated_data.get('content', ''),
            created_by=self.request.user
        )
        
        # Notify collaborators via WebSocket
        self.notify_file_change(project, serializer.instance, 'created')
    
    def perform_update(self, serializer):
        file = self.get_object()
        project = file.project
        
        # Check if user has permission to update files
        if project.owner != self.request.user and not project.projectcollaborator_set.filter(
            user=self.request.user, role__in=['admin', 'editor']
        ).exists():
            self.permission_denied(self.request)
        
        # Create new version if content changed
        old_content = file.content
        new_content = serializer.validated_data.get('content', old_content)
        
        serializer.save()
        
        if old_content != new_content:
            FileVersion.objects.create(
                file=file,
                content=new_content,
                created_by=self.request.user
            )
            
            # Notify collaborators via WebSocket
            self.notify_file_change(project, file, 'updated')
    
    def perform_destroy(self, instance):
        project = instance.project
        
        # Check if user has permission to delete files
        if project.owner != self.request.user and not project.projectcollaborator_set.filter(
            user=self.request.user, role__in=['admin', 'editor']
        ).exists():
            self.permission_denied(self.request)
        
        # Notify collaborators before deleting
        self.notify_file_change(project, instance, 'deleted')
        
        instance.delete()
    
    def notify_file_change(self, project, file, action):
        channel_layer = get_channel_layer()
        
        # Send to project group
        async_to_sync(channel_layer.group_send)(
            f'project_{project.id}',
            {
                'type': 'file_event',
                'event': {
                    'action': action,
                    'file_id': str(file.id),
                    'file_path': file.path,
                    'user_id': str(self.request.user.id),
                    'username': self.request.user.username
                }
            }
        )
    
    @action(detail=True, methods=['get'])
    def versions(self, request, project_pk=None, pk=None):
        file = self.get_object()
        versions = file.versions.all()
        serializer = FileVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restore_version(self, request, project_pk=None, pk=None):
        file = self.get_object()
        version_id = request.data.get('version_id')
        
        try:
            version = FileVersion.objects.get(id=version_id, file=file)
        except FileVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update file content
        file.content = version.content
        file.save()
        
        # Create new version to record the restoration
        new_version = FileVersion.objects.create(
            file=file,
            content=version.content,
            created_by=request.user
        )
        
        # Notify collaborators
        self.notify_file_change(file.project, file, 'updated')
        
        return Response(FileVersionSerializer(new_version).data)