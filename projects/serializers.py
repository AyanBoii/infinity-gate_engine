from rest_framework import serializers
from .models import Project, ProjectCollaborator, File, FileVersion
from users.serializers import UserSerializer

class ProjectCollaboratorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ProjectCollaborator
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']

class FileVersionSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FileVersion
        fields = ['id', 'content', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at']

class FileSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    versions = FileVersionSerializer(many=True, read_only=True)
    
    class Meta:
        model = File
        fields = ['id', 'name', 'path', 'content', 'created_by', 'created_at', 'updated_at', 'versions']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    collaborators = ProjectCollaboratorSerializer(source='projectcollaborator_set', many=True, read_only=True)
    files = FileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'collaborators', 'files', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)