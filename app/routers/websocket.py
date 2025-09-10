from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Set
import json
import logging
from app.database.connection import get_redis_client
from app.core.security import verify_token
from app.services.auth import AuthService
from app.database.connection import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        # Map user_id to set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map WebSocket to user_id for cleanup
        self.connection_user_map: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's WebSocket."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_user_map[websocket] = user_id
        
        logger.info(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket."""
        if websocket in self.connection_user_map:
            user_id = self.connection_user_map[websocket]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty sets
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from connection map
            del self.connection_user_map[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            
            for connection in self.active_connections[user_id].copy():
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


manager = ConnectionManager()


async def authenticate_websocket(token: str) -> int:
    """Authenticate WebSocket connection and return user_id."""
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        
        return user_id
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time notifications.
    
    Usage: ws://localhost:8000/ws?token=your_jwt_token
    """
    try:
        # Authenticate the connection
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        user_id = await authenticate_websocket(token)
        
        # Connect the user
        await manager.connect(websocket, user_id)
        
        # Start Redis subscription for this user's task updates
        redis_client = await get_redis_client()
        pubsub = redis_client.pubsub()
        
        # Subscribe to task updates for this user
        # Note: You might want to make this more specific to user tasks
        await pubsub.psubscribe("task_updates:*")
        
        try:
            while True:
                # Check for new messages from Redis
                try:
                    # Non-blocking check for Redis messages
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=0.1
                    )
                    
                    if message and message['type'] == 'pmessage':
                        # Parse the task update
                        task_update = json.loads(message['data'])
                        
                        # Send to the user (you might want to filter by user_id)
                        await manager.send_personal_message(
                            {
                                "type": "task_update",
                                "data": task_update
                            },
                            user_id
                        )
                
                except asyncio.TimeoutError:
                    # No message received, continue the loop
                    pass
                
                # Check if WebSocket is still alive
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                except Exception:
                    # Handle ping/pong or other WebSocket messages
                    pass
                
                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.1)
        
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected")
        
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@router.get("/notifications/test/{user_id}")
async def test_notification(user_id: str):
    """Test endpoint to send a notification to a specific user."""
    await manager.send_personal_message(
        {
            "type": "test",
            "message": "This is a test notification",
            "timestamp": "2024-01-01T00:00:00Z"
        },
        user_id
    )
    return {"message": f"Test notification sent to user {user_id}"}
