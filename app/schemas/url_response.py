from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    long_url: str
    expire_at: Optional[datetime]
    created_at: datetime
    
    model_config = {"from_attributes": True}
    
    
class StatusResponse(BaseModel):
    short_code: str
    long_url: str
    click_count: int
    created_a: datetime
    expire_at: Optional[datetime]
    
    model_config = {"from_attributes": True}