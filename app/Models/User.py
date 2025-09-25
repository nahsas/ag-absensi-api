from datetime import datetime
import uuid
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, ForeignKey
from app.Core.Database import Base
from sqlalchemy.orm import relationship

from app.Models.Role import Role

class DinasLuar(Base):
    __tablename__ = 'dinas_luars'

    id = Column(String, primary_key=True, index=True, default=str(uuid.uuid4()))
    judul = Column(String)
    deskripsi = Column(String)
    tanggal_mulai = Column(Date)
    tanggal_selesai = Column(Date)
    approved = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now())

    has_dinas_luar = relationship('HasDinasLuar', back_populates='dinas_luar')

class HasDinasLuar(Base):
    __tablename__ = 'user_dinas_luars'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    dinas_luar_id = Column(String, ForeignKey('dinas_luars.id'))

    dinas_luar = relationship('DinasLuar', back_populates='has_dinas_luar', uselist=False)
    user = relationship('User', back_populates='has_dinas_luar', uselist=False)

class User(Base):
    __tablename__ = 'users';
    
    id = Column(String, primary_key=True, index=True, default=str(uuid.uuid4()))
    nip = Column(String)
    nik = Column(String)
    name = Column(String)
    alamat = Column(String)
    no_hp = Column(String)
    password = Column(String)
    position = Column(String)
    photo_profile = Column(String)
    roles_id = Column(String, ForeignKey('roles.id'))
    isFirstLogin = Column(Boolean)

    role = relationship('Role', uselist=False)
    has_dinas_luar = relationship('HasDinasLuar')

