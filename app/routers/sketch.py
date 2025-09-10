from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db_session
from app.core.deps import get_current_active_user
from app.services.sketch import sketch_service
from app.services.background_tasks import task_manager
from app.schemas.sketch import SketchResponse
from app.models.sketch import Sketch, SketchStatus, SketchStyle, SketchType
from app.models.user import User
from sqlalchemy import select
from typing import Dict, Any, List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sketch", tags=["Sketch Processing"])


async def process_sketch_background(
    sketch_id: str,
    input_key: str,
    method: str,
    config: Optional[Dict[str, Any]] = None
):
    """Background task to process sketch."""
    from app.database.connection import async_session_maker
    
    async with async_session_maker() as db:
        try:
            # Update status to processing
            result = await db.execute(select(Sketch).where(Sketch.id == sketch_id))
            sketch = result.scalars().first()
            
            if not sketch:
                logger.error(f"Sketch {sketch_id} not found")
                return
            
            sketch.status = SketchStatus.PROCESSING
            await db.commit()
            
            # Process the image
            processing_result = await sketch_service.process_image(
                input_key=input_key,
                method=method,
                config=config
            )
            
            if processing_result["success"]:
                # Update sketch with result
                sketch.sketch_image_url = processing_result["download_url"]
                sketch.status = SketchStatus.COMPLETED
            else:
                # Mark as failed
                sketch.status = SketchStatus.FAILED
                logger.error(f"Sketch processing failed: {processing_result.get('error')}")
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Background sketch processing failed: {str(e)}")
            try:
                # Mark as failed
                result = await db.execute(select(Sketch).where(Sketch.id == sketch_id))
                sketch = result.scalars().first()
                if sketch:
                    sketch.status = SketchStatus.FAILED
                    await db.commit()
            except Exception as commit_error:
                logger.error(f"Failed to update sketch status: {str(commit_error)}")


@router.post("/create", response_model=Dict[str, Any])
async def create_sketch(
    input_key: str,
    style: SketchStyle = SketchStyle.PENCIL,
    sketch_type: SketchType = SketchType.BLACK_AND_WHITE,
    method: str = "advanced",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new sketch processing job."""
    
    # Verify the input key belongs to the current user
    if not input_key.startswith(f"uploads/{current_user.id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only process your own uploaded files"
        )
    
    # Validate method
    valid_methods = ["basic", "advanced", "artistic"]
    if method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid method. Must be one of: {valid_methods}"
        )
    
    try:
        logger.info(f"Creating sketch for user {current_user.id} with input_key: {input_key}")
        logger.info(f"Style: {style}, Type: {sketch_type}, Method: {method}")
        
        # Generate output key
        output_key = input_key.replace("uploads/", "sketches/").replace("/", f"/{method}_")
        logger.info(f"Generated output_key: {output_key}")
        
        # Create sketch record
        db_sketch = Sketch(
            original_image_url=f"{settings.aws_endpoint_url}/{input_key}",
            sketch_image_url=f"{settings.aws_endpoint_url}/{output_key}",
            status=SketchStatus.PENDING,
            type=sketch_type,
            style=style,
            user_id=current_user.id
        )
        
        db.add(db_sketch)
        await db.commit()
        await db.refresh(db_sketch)
        
        # Configure processing based on style and type
        config = {
            "sigma_s": 60,
            "sigma_r": 0.07,
            "shade_factor": 0.05,
            "kernel_size": 21,
            "blur_type": "gaussian",
            "edge_preserve": True,
            "texture_enhance": True,
            "contrast": 1.5,
            "brightness": 0,
            "smoothing_factor": 0.9,
        }
        
        # Adjust config based on style
        if style == SketchStyle.CHARCOAL:
            config.update({
                "contrast": 2.0,
                "shade_factor": 0.1,
                "texture_enhance": True
            })
        elif style == SketchStyle.WATERCOLOR:
            config.update({
                "smoothing_factor": 0.7,
                "blur_type": "bilateral",
                "edge_preserve": False
            })
        elif style == SketchStyle.INK:
            config.update({
                "contrast": 1.8,
                "edge_preserve": True,
                "kernel_size": 15
            })
        
        # For now, let's process synchronously to debug the issue
        # TODO: Move back to background processing once we fix the task manager issue
        
        try:
            # Update status to processing
            db_sketch.status = SketchStatus.PROCESSING
            await db.commit()
            
            # Process the image
            logger.info(f"Starting sketch processing for sketch_id: {db_sketch.id}")
            processing_result = await sketch_service.process_image(
                input_key=input_key,
                method=method,
                config=config
            )
            logger.info(f"Processing result: {processing_result}")
            
            if processing_result["success"]:
                # Update sketch with result
                db_sketch.sketch_image_url = processing_result["download_url"]
                db_sketch.status = SketchStatus.COMPLETED
            else:
                # Mark as failed
                db_sketch.status = SketchStatus.FAILED
                logger.error(f"Sketch processing failed: {processing_result.get('error')}")
            
            await db.commit()
            await db.refresh(db_sketch)
            
            return {
                "sketch_id": db_sketch.id,
                "task_id": f"sync_{db_sketch.id}",
                "status": db_sketch.status.value,
                "message": "Sketch processing completed" if db_sketch.status == SketchStatus.COMPLETED else "Sketch processing failed"
            }
            
        except Exception as processing_error:
            logger.error(f"Sketch processing error: {str(processing_error)}")
            db_sketch.status = SketchStatus.FAILED
            await db.commit()
            
            return {
                "sketch_id": db_sketch.id,
                "task_id": f"sync_{db_sketch.id}",
                "status": db_sketch.status.value,
                "message": f"Sketch processing failed: {str(processing_error)}"
            }
        
    except Exception as e:
        logger.error(f"Failed to create sketch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sketch: {str(e)}"
        )


@router.get("/{sketch_id}", response_model=SketchResponse)
async def get_sketch(
    sketch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific sketch by ID."""
    
    result = await db.execute(
        select(Sketch).where(
            Sketch.id == sketch_id,
            Sketch.user_id == current_user.id
        )
    )
    sketch = result.scalars().first()
    
    if not sketch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sketch not found"
        )
    
    return sketch


@router.get("/", response_model=List[SketchResponse])
async def list_user_sketches(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[SketchStatus] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all sketches for the current user."""
    
    query = select(Sketch).where(Sketch.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Sketch.status == status_filter)
    
    query = query.offset(skip).limit(limit).order_by(Sketch.created_at.desc())
    
    result = await db.execute(query)
    sketches = result.scalars().all()
    
    return sketches


@router.delete("/{sketch_id}")
async def delete_sketch(
    sketch_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a sketch and its associated files."""
    
    result = await db.execute(
        select(Sketch).where(
            Sketch.id == sketch_id,
            Sketch.user_id == current_user.id
        )
    )
    sketch = result.scalars().first()
    
    if not sketch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sketch not found"
        )
    
    try:
        # Delete from database
        await db.delete(sketch)
        await db.commit()
        
        # TODO: Optionally delete files from S3
        # This could be done as a background task
        
        return {"message": "Sketch deleted successfully"}
        
    except Exception as e:
        logger.error(f"Failed to delete sketch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sketch: {str(e)}"
        )


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a background task."""
    
    task_status = await task_manager.get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return task_status


@router.get("/styles/available")
async def get_available_styles():
    """Get all available sketch styles and methods."""
    
    return {
        "styles": [style.value for style in SketchStyle],
        "types": [sketch_type.value for sketch_type in SketchType],
        "methods": ["basic", "advanced", "artistic"],
        "descriptions": {
            "basic": "Simple pencil sketch with basic edge detection",
            "advanced": "High-quality sketch with edge preservation and texture enhancement",
            "artistic": "Artistic sketch with enhanced details and sharpening"
        }
    }
