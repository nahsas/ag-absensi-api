from sqlalchemy import UUID, Column, String, Time
from app.Core.Database import Base


class SettingJam(Base):
    __tablename__ = 'setting_jams'

    id = Column(UUID(as_uuid=True), primary_key=True)
    nama_jam = Column(String)
    jam = Column(Time)
    batas_jam = Column(Time)