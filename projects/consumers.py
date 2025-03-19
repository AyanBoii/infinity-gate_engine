import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Project, File
from users.models import User

class ProjectConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'project_{self.project_id}'
        
        # Check if user has access to this project
        if not await self.user_can_access_project():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current users in the project
        await self.send_active_users()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others that user has left
        if hasattr(self, 'user_id'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_event',
                    'event': {
                        'action': 'left',
                        'user_id': self.user_id,
                        'username': self.username
                    }
                }
            )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'join':
            # User joining the project
            self.user_id = data.get('user_id')
            self.username = data.get('username')
            
            # Notify others that user has joined
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_event',
                    'event': {
                        'action': 'joined',
                        'user_id': self.user_id,
                        'username': self.username
                    }
                }
            )
        
        elif message_type == 'file_edit':
            # User editing a file
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'file_edit',
                    'edit': {
                        'file_id': data.get('file_id'),
                        'user_id': data.get('user_id'),
                        'username': data.get('username'),
                        'cursor_position': data.get('cursor_position'),
                        'content': data.get('content'),
                        'selection': data.get('selection')
                    }
                }
            )
        
        elif message_type == 'chat_message':
            # User sending a chat message
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'user_id': data.get('user_id'),
                        'username': data.get('username'),
                        'content': data.get('content'),
                        'timestamp': data.get('timestamp')
                    }
                }
            )
    
    # Receive message from room group
    async def user_event(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_event',
            'event': event['event']
        }))
    
    async def file_edit(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'file_edit',
            'edit': event['edit']
        }))
    
    async def file_event(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'file_event',
            'event': event['event']
        }))
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    @database_sync_to_async
    def user_can_access_project(self):
        # Get user from scope
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            return False
        
        try:
            project = Project.objects.get(id=self.project_id)
            # Check if user is owner or collaborator
            return (project.owner_id == user.id or 
                    project.collaborators.filter(id=user.id).exists())
        except Project.DoesNotExist:
            return False
    
    async def send_active_users(self):
        # This would be implemented with a Redis store in production
        # For simplicity, we're not tracking active users in this example
        await self.send(text_data=json.dumps({
            'type': 'active_users',
            'users': []
        }))