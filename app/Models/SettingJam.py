import uuid
from sqlalchemy import UUID, Column, String, Time
from app.Core.Database import Base


class SettingJam(Base):
    __tablename__ = 'setting_jams'

    id = Column(String, primary_key=True, default=str(uuid.uuid4()))
    nama_jam = Column(String)
    jam = Column(Time)
    batas_jam = Column(Time)