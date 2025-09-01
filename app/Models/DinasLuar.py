from app.Core.Database import Base


class DinasLuar(Base):
    __tablename__ = 'dinas_luar'

    # id = Column(, primary_key=True, autoincrement=True)
    # nama = Column(String(100), nullable=False)
    # nip = Column(String(20), nullable=False)
    # jabatan = Column(String(50), nullable=False)
    # tujuan = Column(String(200), nullable=False)
    # tanggal_berangkat = Column(Date, nullable=False)
    # tanggal_kembali = Column(Date, nullable=False)
    # keterangan = Column(Text, nullable=True)

    # def __repr__(self):
    #     return f"<DinasLuar(nama={self.nama}, nip={self.nip}, tujuan={self.tujuan})>"