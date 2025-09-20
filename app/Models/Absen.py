from datetime import datetime
import uuid
import pytz
from sqlalchemy import UUID, Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from app.Core.Database import Base
from sqlalchemy.orm import relationship

class Absen(Base):
    __tablename__ = 'absens'

    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    keterangan = Column(String, nullable=False)
    bukti = Column(String, nullable=True)
    point = Column(Integer, nullable=False)
    tanggal_absen = Column(DateTime, nullable=False, default=datetime.now(pytz.timezone('Asia/Jakarta')))
    show = Column(Boolean, default=True, nullable=False)
    jam_lembur = Column(Integer, default=0, nullable=True)
    lembur_start = Column(DateTime, nullable=True)
    lembur_end = Column(DateTime, nullable=True)

    user = relationship('User', uselist=False)