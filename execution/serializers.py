from rest_framework import serializers
from .models import ExecutionResult

class ExecutionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionResult
        fields = ['id', 'project', 'user', 'command', 'status', 'stdout', 'stderr', 
                  'exit_code', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'stdout', 'stderr', 'exit_code', 
                           'created_at', 'updated_at']