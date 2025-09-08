import uuid
from sqlalchemy import UUID, Column, ForeignKey, Integer, String, Time
from app.Core.Database import Base
from sqlalchemy.orm import relationship


class RolesSetting(Base):
    __tablename__ = 'roles_setting'

    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    roles_id = Column(String, ForeignKey('roles.id'))
    name = Column(String)
    jam_id = Column(String, ForeignKey('setting_jams.id'))
    operator = Column(String)
    value = Column(Time)
    point = Column(Integer)

    jam = relationship('SettingJam', uselist=False)