from sqlalchemy import Column, Integer, String
from app.core.mysql import Base


class UserModel(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(Integer, nullable=True, default=0)
