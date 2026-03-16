from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class URL(Base):
    __tablename__ = "urls"
    
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    long_url: Mapped[str] = mapped_column(
        String(2048), nullable=False
    )
    short_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    click_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<URL id={self.id} short_code={self.short_code!r}>"
