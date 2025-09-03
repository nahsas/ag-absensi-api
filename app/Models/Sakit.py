from datetime import datetime
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy import UUID, Boolean, Column, DateTime, ForeignKey, Integer, String
from app.Core.Database import Base

class Sakit(Base):
    __tablename__ = "sakits"
    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    absen_id = Column(UUID(as_uuid=True), ForeignKey('absens.id'), nullable=False)
    bukti_sakit = Column(String, nullable=True)
    tanggal = Column(DateTime, nullable=False, default=datetime.now())
    approved = Column(Boolean, default=None, nullable=True)
    alasan = Column(String, default=None, nullable=True)

Sakit.user = relationship('User')
Sakit.absen = relationship('Absen')
