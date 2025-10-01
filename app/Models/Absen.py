from datetime import datetime
import uuid
import pytz
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, TIMESTAMP
from app.Core.Database import Base
from sqlalchemy.orm import relationship

class Absen(Base):
    __tablename__ = 'absens'

    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    keterangan = Column(String, nullable=False)
    pagi = Column(DateTime, nullable=True, default=None)
    bukti_pagi = Column(String, nullable=True, default=None)
    istirahat = Column(DateTime, nullable=True, default=None)
    bukti_istirahat = Column(String, nullable=True, default=None)
    kembali_kerja = Column(DateTime, nullable=True, default=None)
    bukti_kembali_kerja = Column(String, nullable=True, default=None)
    pulang = Column(DateTime, nullable=True, default=None)
    bukti_pulang = Column(String, nullable=True, default=None)
    mulai_lembur = Column(DateTime, nullable=True, default=None)
    bukti_lembur_mulai = Column(String, nullable=True, default=None)
    selesai_lembur = Column(DateTime, nullable=True, default=None)
    bukti_lembur_selesai = Column(String, nullable=True, default=None)
    lama_lembur = Column(Float, nullable=True, default=0.0)
    lama_bekerja = Column(Float, nullable=True, default=0.0)
    point = Column(Integer, nullable=True, default=0)
    created_at = Column(TIMESTAMP(timezone=pytz.timezone('Asia/Jakarta')),default=datetime.now(pytz.timezone('Asia/Jakarta')).timestamp())
    updated_at = Column(TIMESTAMP(timezone=pytz.timezone('Asia/Jakarta')),default=datetime.now(pytz.timezone('Asia/Jakarta')).timestamp())

    user = relationship('User', uselist=False)