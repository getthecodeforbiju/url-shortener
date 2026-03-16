from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    # Application
    app_name: str = "URL Shortener"
    base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    
    # Database
    database_url: str =  "cockroachdb+psycopg2://root@localhost:26257/urlshortener?sslmode=disable"
    
    # Cache
    dragonfly_url: str = "redis://localhost:6379/0"
    cache_ttl_second: int = 3600
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
