from datetime import datetime
import os
import uuid
from fastapi import Depends, File, HTTPException, UploadFile, status
from fastapi.routing import APIRouter
from pydantic import BaseModel
import pytz
from sqlalchemy import DateTime
from app.Core.Essential import create_izin_code, get_auth_user
from app.Core.Database import get_db
from sqlalchemy.orm import Session
from typing import Optional

from app.Models.Sakit import Sakit
from app.Models.Absen import Absen
from app.Models.User import User

router = APIRouter()

class payload(BaseModel):
    input_time:Optional[str] = f"{datetime.now(pytz.timezone('Asia/Jakarta')).date()} {datetime.now(pytz.timezone('Asia/Jakarta')).time().hour}:{datetime.now(pytz.timezone('Asia/Jakarta')).time().minute}:{datetime.now(pytz.timezone('Asia/Jakarta')).time().second}"

UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get('/get_user_izin')
def get_user_izin(db:Session = Depends(get_db), user_id:str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if user.role.name != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Anda tidak memiliki akses untuk melihat pengajuan izin")
    sakits = db.query(Sakit).where(Sakit.approved == None).all()
    result = []
    for sakit in sakits:
        user = db.query(User).where(User.id == sakit.user_id).first()
        result.append({"id": sakit.id, "user_id": sakit.user_id, "user_nama": user.name if user else "Unknown", "alasan": sakit.alasan, "bukti_sakit": sakit.bukti_sakit, "tanggal": sakit.tanggal, "approved": sakit.approved, "code": sakit.code})
    return result

@router.post('/set_approve/{izin_id}')
async def set_approve(izin_id:str, approve:bool, db:Session = Depends(get_db), user_id:str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user or not user.role != 'superadmin':
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Anda tidak memiliki akses untuk menyetujui pengajuan izin")
    sakit = db.query(Sakit).where(Sakit.id == izin_id).first()
    if not sakit:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pengajuan izin tidak ditemukan")
    if sakit.approved is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Pengajuan izin sudah disetujui atau ditolak sebelumnya")
    sakit.approved = approve
    
    db.commit()
    db.refresh(sakit)

    start_date = datetime.replace(sakit.tanggal, hour=0, minute=0, second=0)
    end_date = datetime.replace(sakit.tanggal, hour=23, minute=59, second=59)
    print(start_date)
    print(end_date)
    absent_to_delete = db.query(Absen).where(Absen.keterangan == 'tanpa_keterangan').where(start_date <= Absen.created_at).where(Absen.created_at <= end_date).first()
    if absent_to_delete and approve:
        db.delete(absent_to_delete)
        db.commit()

    return {"message":"Pengajuan izin berhasil disetujui" if approve else "Pengajuan izin berhasil ditolak"}

@router.post('/add_sakit')
async def add_sakit(alasan:Optional[str] = None, supabase_url:Optional[str] = None, input_time:datetime = datetime.now(pytz.timezone('Asia/Jakarta')),bukti_kembali: UploadFile = File(...), db:Session = Depends(get_db),user_id:str = Depends(get_auth_user)):
    # try:
        input_time = datetime.now(pytz.timezone('Asia/Jakarta')) if input_time == None else input_time
        user = db.query(User).where(User.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User tidak ditemukan")
        new_absen = Absen(
            id=str(uuid.uuid4()),
            user_id=user.id,
            keterangan="izin",
            created_at=input_time,
        )
        db.add(new_absen)
        db.flush()
        
        code = create_izin_code(user_id=user.id, db=db)

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
            bukti_sakit = supabase_url if supabase_url else bukti_url,
            tanggal = input_time,
            alasan = alasan,
            approved = None,
            
            created_at = input_time,
            code = code
        )

        db.add(new_sakit)
        db.commit()
        return {"message":"Bukti izin sudah diajukan"}