# game_engine/core/engine.py

import uuid
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Import our database connectors
from game_engine.database.db_connector import PostgreSQLConnector
from game_engine.core.game_loop import GameLoop, GameState, GameAction, GameSession

# Redis connector for caching and real-time operations
class RedisConnector:
    """Connector for Redis caching and real-time operations."""
    
    def __init__(self, redis_url, ttl=300):
        """
        Initialize the Redis connector.
        
        Args:
            redis_url: Connection URL for Redis
            ttl: Time-to-live for cached items (in seconds)
        """
        import redis
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl
        
    async def cache_scene(self, session_id: str, scene_data: Dict[str, Any]) -> bool:
        """Cache scene data for quick retrieval."""
        try:
            key = f"scene:{session_id}"
            self.redis.setex(key, self.ttl, json.dumps(scene_data))
            return True
        except Exception as e:
            logging.error(f"Redis cache error: {e}")
            return False
            
    async def get_cached_scene(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached scene data if available."""
        try:
            key = f"scene:{session_id}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logging.error(f"Redis get error: {e}")
            return None
            
    async def publish_update(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish an update to a Redis channel."""
        try:
            self.redis.publish(channel, json.dumps(message))
            return True
        except Exception as e:
            logging.error(f"Redis publish error: {e}")
            return False
            
    async def add_to_action_buffer(self, session_id: str, action: Dict[str, Any]) -> bool:
        """Add action to temporary buffer for undo/redo functionality."""
        try:
            key = f"action_buffer:{session_id}"
            buffer = self.redis.get(key)
            if buffer:
                actions = json.loads(buffer)
                actions.append(action)
                # Keep only the last 20 actions
                if len(actions) > 20:
                    actions = actions[-20:]
            else:
                actions = [action]
                
            self.redis.setex(key, self.ttl, json.dumps(actions))
            return True
        except Exception as e:
            logging.error(f"Redis action buffer error: {e}")
            return False
            
    async def rate_limit_check(self, key: str, limit: int, window: int) -> bool:
        """Check if operation exceeds rate limit."""
        try:
            current = self.redis.get(key)
            if current and int(current) >= limit:
                return False
                
            pipeline = self.redis.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, window)
            pipeline.execute()
            return True
        except Exception as e:
            logging.error(f"Redis rate limit error: {e}")
            # Allow operation in case of Redis failure
            return True


# Celery task queue manager
class TaskQueueManager:
    """Manages asynchronous tasks using Celery."""
    
    def __init__(self, celery_app):
        """
        Initialize with a Celery app instance.
        
        Args:
            celery_app: Initialized Celery application
        """
        self.celery = celery_app
        
    def schedule_task(self, task_name, *args, **kwargs):
        """Schedule a task for asynchronous execution."""
        return self.celery.send_task(task_name, args=args, kwargs=kwargs)
        
    def check_task_status(self, task_id):
        """Check the status of a scheduled task."""
        return self.celery.AsyncResult(task_id)


# WebSocket manager for real-time communication
class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.connected_clients = {}
    
    async def register_client(self, session_id, websocket):
        """Register a new client connection."""
        if session_id not in self.connected_clients:
            self.connected_clients[session_id] = set()
        self.connected_clients[session_id].add(websocket)
        
    async def unregister_client(self, session_id, websocket):
        """Unregister a client connection."""
        if session_id in self.connected_clients:
            self.connected_clients[session_id].discard(websocket)
            if not self.connected_clients[session_id]:
                del self.connected_clients[session_id]
                
    async def broadcast(self, session_id, message):
        """Broadcast a message to all clients for a session."""
        if session_id in self.connected_clients:
            dead_clients = set()
            for websocket in self.connected_clients[session_id]:
                try:
                    await websocket.send(json.dumps(message))
                except Exception:
                    dead_clients.add(websocket)
            
            # Clean up dead connections
            for dead in dead_clients:
                self.connected_clients[session_id].discard(dead)


# Main game engine class
class DnDGameEngine:
    """
    Main game engine for the Multimodal D&D Generator.
    Handles the core game loop and state management.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the game engine with configuration parameters.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        self.session_id = config.get('session_id', str(uuid.uuid4()))
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, 
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connections
        self._init_db_connections()
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Initialize game session
        self.game_session = GameSession(
            session_id=self.session_id,
            db_connector=self.pg_connector
        )
        
        # Create Celery app for task queue
        from celery import Celery
        self.celery = Celery('dnd_game_engine',
                           broker=self.config.get('redis_url'),
                           backend=self.config.get('redis_url'))
        
        # Task queue manager
        self.task_manager = TaskQueueManager(self.celery)
        
        self.logger.info(f"Game Engine initialized with session ID: {self.session_id}")
    
    def _init_db_connections(self):
        """Initialize database connections to PostgreSQL and Redis"""
        # PostgreSQL connection
        self.pg_connector = PostgreSQLConnector(
            use_async=self.config.get('use_async', True)
        )
        
        # Redis connection
        self.redis_connector = RedisConnector(
            redis_url=self.config.get('redis_url', 'redis://localhost:6379/0'),
            ttl=self.config.get('redis_ttl', 300)
        )
        
        self.logger.info("Database connections initialized")
    
    async def create_new_game(self, player_id: str, initial_state: Optional[Dict[str, Any]] = None) -> str:
        """Create a new game session."""
        self.logger.info(f"Creating new game for player {player_id}")
        
        # Create game in PostgreSQL
        session_id = await self.game_session.start_new_session(player_id, initial_state)
        
        # Cache initial state in Redis
        presentation = await self.game_session.game_loop.presentation()
        await self.redis_connector.cache_scene(session_id, presentation)
        
        # Broadcast creation event
        await self.notify_game_update(session_id, "game_created", {
            "session_id": session_id,
            "player_id": player_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return session_id
    
    async def load_game(self, session_id: str) -> Dict[str, Any]:
        """Load an existing game session."""
        self.logger.info(f"Loading game session {session_id}")
        
        # Check Redis cache first
        cached_scene = await self.redis_connector.get_cached_scene(session_id)
        if cached_scene:
            self.logger.info(f"Retrieved session {session_id} from cache")
            return cached_scene
        
        # Load from PostgreSQL if not in cache
        success = await self.game_session.load_session(session_id)
        if success:
            # Generate presentation and cache it
            presentation = await self.game_session.game_loop.presentation()
            await self.redis_connector.cache_scene(session_id, presentation)
            return presentation
        else:
            self.logger.error(f"Failed to load session {session_id}")
            return {"error": "Session not found", "session_id": session_id}
    
    async def process_game_action(self, session_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process a player action through the game loop."""
        self.logger.info(f"Processing action for session {session_id}: {action}")
        
        # Rate limit check for actions
        rate_limited = await self.redis_connector.rate_limit_check(
            f"action_rate:{session_id}", 
            self.config.get('action_rate_limit', 10),
            self.config.get('action_rate_window', 60)
        )
        
        if not rate_limited:
            return {"error": "Rate limit exceeded", "session_id": session_id}
        
        # Add to action buffer for undo/redo
        await self.redis_connector.add_to_action_buffer(session_id, action)
        
        # Process through game loop
        result = await self.game_session.process_action(action)
        
        # Cache updated scene
        if "presentation" in result:
            await self.redis_connector.cache_scene(session_id, result["presentation"])
        
        # Broadcast update
        await self.notify_game_update(session_id, "state_updated", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    async def notify_game_update(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Notify connected clients about game updates."""
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Publish to Redis for other server instances
        channel = f"game_updates:{session_id}"
        await self.redis_connector.publish_update(channel, message)
        
        # Broadcast to WebSocket clients
        await self.ws_manager.broadcast(session_id, message)
    
    async def handle_llm_generation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Template for LLM integration - to be implemented."""
        # Placeholder for LLM integration
        self.logger.info("LLM generation requested (not yet implemented)")
        
        # This would typically be implemented as:
        # 1. Prepare prompt based on context
        # 2. Call LLM API
        # 3. Parse response
        # 4. Update game state
        
        return {
            "text_content": f"Description for {context.get('location', 'unknown')}",
            "generated": False,  # Indicates this is a placeholder
        }
    
    async def handle_image_generation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Template for Stable Diffusion integration - to be implemented."""
        # Placeholder for Stable Diffusion integration
        self.logger.info("Image generation requested (not yet implemented)")
        
        # This would typically be implemented as:
        # 1. Prepare prompt based on context
        # 2. Call SD API
        # 3. Store/process image
        # 4. Return image reference
        
        return {
            "image_url": None,
            "generated": False,  # Indicates this is a placeholder
        }
    
    async def save_game_state(self, session_id: str) -> bool:
        """Explicitly save the current game state."""
        return await self.game_session.save_session()
    
    def register_websocket(self, session_id: str, websocket):
        """Register a WebSocket connection for real-time updates."""
        return self.ws_manager.register_client(session_id, websocket)
    
    def unregister_websocket(self, session_id: str, websocket):
        """Unregister a WebSocket connection."""
        return self.ws_manager.unregister_client(session_id, websocket)
    
    async def handle_failover(self, session_id: str) -> bool:
        """Handle failover recovery for a session."""
        self.logger.warning(f"Attempting failover recovery for session {session_id}")
        
        try:
            # Attempt to load from PostgreSQL
            success = await self.game_session.load_session(session_id)
            if not success:
                self.logger.error(f"Failover failed: Session {session_id} not found in database")
                return False
            
            # Regenerate Redis cache
            presentation = await self.game_session.game_loop.presentation()
            await self.redis_connector.cache_scene(session_id, presentation)
            
            self.logger.info(f"Failover recovery successful for session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failover error for session {session_id}: {e}")
            return False


# Factory function to create and configure the game engine
async def create_game_engine(config: Dict[str, Any]) -> DnDGameEngine:
    """
    Create and initialize a game engine instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized DnDGameEngine instance
    """
    engine = DnDGameEngine(config)
    return engine