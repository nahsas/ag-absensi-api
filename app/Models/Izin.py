from datetime import datetime
import uuid
from sqlalchemy import UUID, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from . import Absen

Base = declarative_base()

class Absen(Base):
    __tablename__ = 'absens'

    id = Column(String,primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    keterangan = Column(String, nullable=False)
    bukti = Column(String, nullable=True)
    point = Column(Integer, nullable=False)
    tanggal_absen = Column(DateTime, nullable=False, default=datetime.now())
    show = Column(Boolean, default=True, nullable=False)

class User(Base):
    __tablename__ = 'users';

    id = Column(String, primary_key=True , default=str(uuid.uuid4()))
    nip = Column(String)
    nik = Column(String)
    name = Column(String)
    alamat = Column(String)
    no_hp = Column(String)
    password = Column(String)
    roles_id = Column(String, ForeignKey('roles.id'))
    isFirstLogin = Column(Boolean)


class Izin(Base):
    __tablename__ = 'izins'

    id = Column(String, primary_key=True, default=str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'))  # Asumsi ada tabel 'users'
    absen_id = Column(String, ForeignKey('absens.id')) # Asumsi ada tabel 'absens'
    bukti_kembali = Column(String)
    alasan = Column(String)
    jam_kembali = Column(DateTime)
    keluar_selama = Column(Integer)
    approved = Column(Boolean,nullable=True)
    judul = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Definisi relasi, jika Anda memiliki model User dan Absen

Izin.absen = relationship("Absen")

Izin.user = relationship("User")