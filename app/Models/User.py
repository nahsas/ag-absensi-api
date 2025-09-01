from sqlalchemy import UUID, Boolean, Column, String, ForeignKey
from app.Core.Database import Base
from sqlalchemy.orm import relationship

from app.Models.Role import Role

class User(Base):
    __tablename__ = 'users';

    id = Column(UUID(as_uuid=True), primary_key=True)
    nip = Column(String)
    nik = Column(String)
    name = Column(String)
    alamat = Column(String)
    no_hp = Column(String)
    password = Column(String)
    position = Column(String)
    roles_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'))
    isFirstLogin = Column(Boolean)

    role = relationship('Role', uselist=False)