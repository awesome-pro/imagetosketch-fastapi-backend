from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.models.sketch import SketchStatus, SketchType, SketchStyle
from app.utils.pagination import PaginatedResponse

class SketchBase(BaseModel):
    original_image_url: str
    sketch_image_url: str
    type: SketchType = SketchType.COLOR
    style: SketchStyle = SketchStyle.PENCIL

class SketchCreate(SketchBase):
    status: SketchStatus = SketchStatus.PENDING
    type: SketchType = SketchType.COLOR
    style: SketchStyle = SketchStyle.PENCIL

class SketchUpdate(SketchBase):
    status: Optional[SketchStatus] = None
    type: Optional[SketchType] = None
    style: Optional[SketchStyle] = None

class SketchResponse(SketchBase):
    id: str
    status: SketchStatus
    created_at: datetime
    updated_at: datetime

class SketchListResponse(PaginatedResponse[SketchResponse]):
    pass
