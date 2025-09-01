from datetime import datetime
import uuid
from sqlalchemy import UUID, Boolean, Column, DateTime, ForeignKey, Integer, String
from app.Core.Database import Base
from sqlalchemy.orm import relationship

class Absen(Base):
    __tablename__ = 'absens'

    id = Column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    keterangan = Column(String, nullable=False)
    bukti = Column(String, nullable=True)
    point = Column(Integer, nullable=False)
    tanggal_absen = Column(DateTime, nullable=False, default=datetime.now())
    show = Column(Boolean, default=True, nullable=False)

    user = relationship('User', uselist=False)