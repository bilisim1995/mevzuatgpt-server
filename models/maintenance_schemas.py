"""
Maintenance mode schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MaintenanceStatusResponse(BaseModel):
    """Maintenance mode status response for users"""
    is_enabled: bool = Field(..., description="Whether maintenance mode is active")
    title: str = Field(..., description="Maintenance mode title")
    message: str = Field(..., description="Maintenance mode message")
    start_time: Optional[datetime] = Field(None, description="Maintenance start time")
    end_time: Optional[datetime] = Field(None, description="Maintenance end time")
    

class MaintenanceUpdateRequest(BaseModel):
    """Admin request to update maintenance mode"""
    is_enabled: bool = Field(..., description="Enable or disable maintenance mode")
    title: Optional[str] = Field(None, max_length=200, description="Maintenance title")
    message: Optional[str] = Field(None, description="Maintenance message")
    start_time: Optional[datetime] = Field(None, description="Maintenance start time")
    end_time: Optional[datetime] = Field(None, description="Maintenance end time")


class MaintenanceDetailResponse(BaseModel):
    """Detailed maintenance mode response for admins"""
    id: str = Field(..., description="Maintenance record ID")
    is_enabled: bool = Field(..., description="Whether maintenance mode is active")
    title: str = Field(..., description="Maintenance mode title")
    message: str = Field(..., description="Maintenance mode message")
    start_time: Optional[datetime] = Field(None, description="Maintenance start time")
    end_time: Optional[datetime] = Field(None, description="Maintenance end time")
    updated_by: Optional[str] = Field(None, description="Admin who last updated")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")