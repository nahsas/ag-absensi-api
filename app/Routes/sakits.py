from datetime import datetime
import os
import uuid
from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.routing import APIRouter
from pydantic import BaseModel
from sqlalchemy import DateTime
from app.Core.Essential import get_auth_user
from app.Core.Database import get_db
from sqlalchemy.orm import Session
from typing import Optional

from app.Models.Sakit import Sakit
from app.Models.Absen import Absen
from app.Models.User import User

router = APIRouter()

class payload(BaseModel):
    input_time:Optional[str] = f"{datetime.now().date()} {datetime.now().time().hour}:{datetime.now().time().minute}:{datetime.now().time().second}"

UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post('/add_sakit')
async def add_sakit(alasan:Optional[str] = None, input_time:datetime = datetime.now(),bukti_kembali: UploadFile = File(...), db:Session = Depends(get_db),user_id:str = Depends(get_auth_user)):
    # try:
        input_time = datetime.now() if input_time == None else input_time
        user = db.query(User).where(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User tidak ditemukan")
        new_absen = Absen(
            id=str(uuid.uuid4()),
            user_id=user.id,
            keterangan="sakit",
            point=0, # point akan dihitung saat kembali
            tanggal_absen=input_time,
            show=True
        )
        db.add(new_absen)
        db.flush()
        
        bukti_url = None
        if bukti_kembali and bukti_kembali.filename:
            ext = os.path.splitext(bukti_kembali.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(await bukti_kembali.read())
            bukti_url = f"/absen/absen-image/{filename}"
        new_sakit = Sakit(
            id = str(uuid.uuid4()),
            user_id = user.id,
            absen_id = new_absen.id,
            bukti_sakit = bukti_url,
            tanggal = input_time,
            alasan = alasan,
            approved = None
        )

        db.add(new_sakit)
        db.commit()
        return {"message":"Bukti sakit sudah diajukan"}
    # except Exception:
    #     raise HTTPException(status.HTTP_400_BAD_REQUEST,detail=f"Gagal mengajukan bukti sakit")