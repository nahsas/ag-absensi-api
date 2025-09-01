from sqlalchemy import UUID, Column, ForeignKey, Integer, String
from app.Core.Database import Base
from sqlalchemy.orm import relationship


class RolesSetting(Base):
    __tablename__ = 'roles_setting'

    id = Column(UUID(as_uuid=True),primary_key=True)
    roles_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'))
    name = Column(String)
    jam_id = Column(String, ForeignKey('setting_jams.id'))
    operator = Column(String)
    value = Column(Integer)
    point = Column(Integer)

    jam = relationship('SettingJam', uselist=False)