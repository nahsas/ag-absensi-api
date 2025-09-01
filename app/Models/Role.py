from sqlalchemy import UUID, Column, String
from app.Core.Database import Base


class Role(Base):
    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String)