import uuid

from sqlalchemy import Column, String
from app.Core.Database import Base


class Setting(Base):
    __tablename__ = 'settings'

    id = Column(String, primary_key=True, default=str(uuid.uuid4))
    name = Column(String, unique=True)
    type = Column(String)
    value = Column(String)