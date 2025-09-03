from sqlalchemy import UUID, Boolean, Column, String, ForeignKey
from app.Core.Database import Base
from sqlalchemy.orm import relationship

from app.Models.Role import Role

class User(Base):
    __tablename__ = 'users';
    
    # MySQL ga punya tipe native UUID, jadi lebih aman disimpan sebagai VARCHAR(36)
    id = Column(String, primary_key=True, index=True, default=str(uuid.uuid4()))
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