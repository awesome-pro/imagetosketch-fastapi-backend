from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base
import enum
import uuid


class SketchStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SketchType(str, enum.Enum):
    BLACK_AND_WHITE = "black_and_white"
    COLOR = "color"

class SketchStyle(str, enum.Enum):
    PENCIL = "pencil"
    WATERCOLOR = "watercolor"
    OIL = "oil"
    ACRYLIC = "acrylic"
    PASTEL = "pastel"
    CHARCOAL = "charcoal"
    INK = "ink"
    OTHER = "other"

class Sketch(Base):
    __tablename__ = "sketches"

    id = Column(String(255), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    original_image_url = Column(Text, nullable=False)
    sketch_image_url = Column(Text, nullable=False)
    status = Column(Enum(SketchStatus), default=SketchStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    type = Column(Enum(SketchType), default=SketchType.COLOR, nullable=False)
    style = Column(Enum(SketchStyle), default=SketchStyle.PENCIL, nullable=False)
    
    # Foreign Key
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="sketches")

