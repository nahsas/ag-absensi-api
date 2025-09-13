from datetime import datetime
import pytz
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy import UUID, Boolean, Column, DateTime, ForeignKey, Integer, String
from app.Core.Database import Base

class Sakit(Base):
    __tablename__ = "sakits"
    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    absen_id = Column(String, ForeignKey('absens.id'), nullable=False)
    bukti_sakit = Column(String, nullable=True)
    tanggal = Column(DateTime, nullable=False, default=datetime.now(pytz.timezone('Asia/Jakarta')))
    approved = Column(Boolean, default=None, nullable=True)
    alasan = Column(String, default=None, nullable=True)
    code = Column(String, default=None, nullable=True)

Sakit.user = relationship('User')
Sakit.absen = relationship('Absen')
