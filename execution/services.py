import docker
import tempfile
import os
import shutil
import uuid
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ExecutionResult
from projects.models import Project, File

class CodeExecutionService:
    def __init__(self):
        self.client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)
    
    def execute_code(self, project_id, user_id, command):
        """
        Execute code for a project in a Docker container
        """
        try:
            # Create execution record
            project = Project.objects.get(id=project_id)
            execution = ExecutionResult.objects.create(
                project=project,
                user_id=user_id,
                command=command,
                status='pending'
            )
            
            # Update status to running
            execution.status = 'running'
            execution.save()
            
            # Notify via WebSocket
            self._notify_execution_update(execution)
            
            # Create temporary directory for project files
            temp_dir = tempfile.mkdtemp()
            try:
                # Write project files to temp directory
                self._write_project_files(project, temp_dir)
                
                # Run code in Docker container
                container_name = f"codehive-execution-{uuid.uuid4()}"
                container = self.client.containers.run(
                    "python:3.9-slim",  # Base image
                    command=command,
                    volumes={temp_dir: {'bind': '/app', 'mode': 'rw'}},
                    working_dir='/app',
                    detach=True,
                    name=container_name,
                    remove=True
                )
                
                # Wait for container to finish with timeout
                try:
                    exit_code = container.wait(timeout=settings.CODE_EXECUTION_TIMEOUT)['StatusCode']
                    stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
                    stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
                    
                    # Update execution record
                    execution.status = 'completed'
                    execution.stdout = stdout
                    execution.stderr = stderr
                    execution.exit_code = exit_code
                    execution.save()
                    
                except docker.errors.NotFound:
                    # Container was removed before we could get logs
                    execution.status = 'failed'
                    execution.stderr = 'Execution failed: container was removed'
                    execution.save()
                
                except Exception as e:
                    # Handle timeout or other errors
                    try:
                        container.kill()
                    except:
                        pass
                    
                    execution.status = 'failed'
                    execution.stderr = f'Execution failed: {str(e)}'
                    execution.save()
            
            finally:
                # Clean up temp directory
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Notify via WebSocket
            self._notify_execution_update(execution)
            
            return execution
        
        except Exception as e:
            # Handle any other exceptions
            execution = ExecutionResult.objects.create(
                project_id=project_id,
                user_id=user_id,
                command=command,
                status='failed',
                stderr=f'Execution setup failed: {str(e)}'
            )
            
            # Notify via WebSocket
            self._notify_execution_update(execution)
            
            return execution
    
    def _write_project_files(self, project, temp_dir):
        """
        Write project files to a temporary directory
        """
        files = File.objects.filter(project=project)
        
        for file in files:
            # Create directories if needed
            file_path = os.path.join(temp_dir, file.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file content
            with open(file_path, 'w') as f:
                f.write(file.content)
    
    def _notify_execution_update(self, execution):
        """
        Notify clients about execution updates via WebSocket
        """
        channel_layer = get_channel_layer()
        
        # Send to project group
        async_to_sync(channel_layer.group_send)(
            f'project_{execution.project_id}',
            {
                'type': 'execution_update',
                'execution': {
                    'id': str(execution.id),
                    'status': execution.status,
                    'command': execution.command,
                    'stdout': execution.stdout,
                    'stderr': execution.stderr,
                    'exit_code': execution.exit_code,
                    'created_at': execution.created_at.isoformat(),
                    'updated_at': execution.updated_at.isoformat(),
                    'user_id': str(execution.user_id) if execution.user_id else None
                }
            }
        )