from sqlalchemy import Column, Date, Integer, String, ForeignKey
from app.Core.Database import Base
from sqlalchemy.orm import relationship

class UserLembur(Base):
    __tablename__ = "user_has_lemburs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    lembur_id = Column(String, ForeignKey("lemburs.id"))

    lembur = relationship("Lembur")
    user = relationship("User")

class Lembur(Base):
    __tablename__ = "lemburs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, index=True, nullable=False)
    start_date = Column(Date, nullable=True)
