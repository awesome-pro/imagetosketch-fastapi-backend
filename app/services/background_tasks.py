import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Coroutine
from datetime import datetime, timedelta
from app.core.config import settings
from app.database.connection import get_redis_client
import json
import uuid

logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class BackgroundTaskManager:
    """
    Background task manager optimized for Google Cloud Run.
    Uses Redis for task state management and coordination.
    """
    
    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)
    
    async def submit_task(
        self,
        task_func: Callable[..., Coroutine],
        task_id: Optional[str] = None,
        timeout: int = settings.task_timeout,
        **kwargs
    ) -> str:
        """
        Submit a background task for execution.
        
        Args:
            task_func: The async function to execute
            task_id: Optional task ID (will generate if not provided)
            timeout: Task timeout in seconds
            **kwargs: Arguments to pass to the task function
            
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        # Store task metadata in Redis
        redis_client = await get_redis_client()
        task_metadata = {
            "id": task_id,
            "status": TaskStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "timeout": timeout,
            "function": task_func.__name__,
            "kwargs": json.dumps(kwargs, default=str)  # Serialize kwargs
        }
        
        await redis_client.setex(
            f"task:{task_id}",
            timedelta(hours=24).total_seconds(),  # Keep task info for 24 hours
            json.dumps(task_metadata)
        )
        
        # Create and start the task
        task = asyncio.create_task(
            self._execute_task(task_func, task_id, timeout, **kwargs)
        )
        self.running_tasks[task_id] = task
        
        logger.info(f"Submitted task {task_id} ({task_func.__name__})")
        return task_id
    
    async def _execute_task(
        self,
        task_func: Callable[..., Coroutine],
        task_id: str,
        timeout: int,
        **kwargs
    ):
        """Execute a task with proper error handling and status updates."""
        redis_client = await get_redis_client()
        
        async with self.semaphore:
            try:
                # Update status to running
                await self._update_task_status(task_id, TaskStatus.RUNNING)
                
                # Execute the task with timeout
                await asyncio.wait_for(
                    task_func(**kwargs),
                    timeout=timeout
                )
                
                # Mark as completed
                await self._update_task_status(task_id, TaskStatus.COMPLETED)
                logger.info(f"Task {task_id} completed successfully")
                
            except asyncio.TimeoutError:
                await self._update_task_status(task_id, TaskStatus.TIMEOUT)
                logger.error(f"Task {task_id} timed out after {timeout} seconds")
                
            except Exception as e:
                await self._update_task_status(
                    task_id, 
                    TaskStatus.FAILED, 
                    error=str(e)
                )
                logger.error(f"Task {task_id} failed: {str(e)}")
                
            finally:
                # Clean up
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]
    
    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """Update task status in Redis."""
        redis_client = await get_redis_client()
        
        # Get existing task data
        task_data_json = await redis_client.get(f"task:{task_id}")
        if task_data_json:
            task_data = json.loads(task_data_json)
        else:
            task_data = {"id": task_id}
        
        # Update status and metadata
        task_data.update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        if error:
            task_data["error"] = error
        
        if result:
            task_data["result"] = result
        
        # Store updated data
        await redis_client.setex(
            f"task:{task_id}",
            timedelta(hours=24).total_seconds(),
            json.dumps(task_data)
        )
        
        # Publish status update for real-time notifications
        await redis_client.publish(
            f"task_updates:{task_id}",
            json.dumps({
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "error": error,
                "result": result
            })
        )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task."""
        redis_client = await get_redis_client()
        task_data_json = await redis_client.get(f"task:{task_id}")
        
        if task_data_json:
            return json.loads(task_data_json)
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            await self._update_task_status(task_id, "cancelled")
            logger.info(f"Task {task_id} cancelled")
            return True
        
        return False
    
    async def list_user_tasks(
        self,
        user_id: str,
        status_filter: Optional[str] = None
    ) -> list:
        """List tasks for a specific user."""
        redis_client = await get_redis_client()
        
        # Get all task keys
        task_keys = await redis_client.keys("task:*")
        user_tasks = []
        
        for key in task_keys:
            task_data_json = await redis_client.get(key)
            if task_data_json:
                task_data = json.loads(task_data_json)
                
                # Check if task belongs to user (you might need to adjust this logic)
                # For now, we'll include all tasks - you can filter by user_id in kwargs
                if status_filter and task_data.get("status") != status_filter:
                    continue
                
                user_tasks.append(task_data)
        
        return sorted(user_tasks, key=lambda x: x.get("created_at", ""), reverse=True)


# Global task manager instance
task_manager = BackgroundTaskManager()
