from datetime import datetime 
from typing import Optional
import re
from pydantic import BaseModel, HttpUrl, field_validator, model_validator

ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_alias: Optional[str] = None
    expire_at: Optional[datetime] = None
    
    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not ALIAS_PATTERN.match(v):
            raise ValueError(
                "Alias must be 3 - 32 characters: letters, digits, hyphens, underscores only."
            )
        return v
    
    @model_validator(mode="after")
    def validate_expiry(self) -> "ShortenRequest":
        if self.expire_at:
            now = datetime.utcnow().replace(tzinfo=self.expire_at.tzinfo)
            if self.expire_at <= now:
                raise ValueError("expire_at must be a future datetime")
        return self    
        
        