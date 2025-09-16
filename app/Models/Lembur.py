import uuid

from sqlalchemy import Column, Date, String
from app.Core.Database import Base
from sqlalchemy.orm import relationship

class Lembur(Base):
    __tablename__ = "lemburs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, index=True, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
