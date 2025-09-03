import uuid
from sqlalchemy import UUID, Column, String
from app.Core.Database import Base


class Role(Base):
    __tablename__ = 'roles'

    id = Column(String, primary_key=True, default=str(uuid.uuid4()))
    name = Column(String)