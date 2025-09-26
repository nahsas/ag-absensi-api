from datetime import datetime
import os
from typing import Optional, Union
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
import pytz
from sqlalchemy.orm import Session, joinedload
from app.Core.Database import get_db
from app.Core.Essential import check_libur, get_auth_user
from app.Models.Absen import Absen
from app.Models.SettingJam import SettingJam
from app.Models.User import User
from app.Models.Izin import Izin # Import model Izin

router = APIRouter()

class izin_input(BaseModel):
    judul : Union[str,None] = None,
    input : Union[str,None] = None,
    alasan : str = ''

@router.post('/add-izin')
async def add_izin(
    data:izin_input,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_auth_user)
):    
    if check_libur(db):
        return {"Tidak ada izin keluar kantor hari ini dikarenakan sedang libur"}

    try:
        input_time = datetime.now(pytz.timezone('Asia/Jakarta')) if data.input is None else datetime.fromisoformat(data.input)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format datetime tidak valid. Gunakan format ISO 8601 (contoh: '2025-08-23T10:00:00')."
        )
    
    check_active_izin = db.query(Izin).where(Izin.user_id == user_id).where(Izin.jam_kembali == None).first()

    if check_active_izin:
        return {
            "message":"Kamu sedang dalam status keluar kantor."
        }

    new_absen = Absen(
        id=str(uuid.uuid4()),
        user_id=user_id,
        keterangan="keluar_kantor",
        created_at=input_time
    )
    db.add(new_absen)
    db.commit()
    db.refresh(new_absen)

    new_izin = Izin(
        id=str(uuid.uuid4()),
        user_id = user_id,
        absen_id = new_absen.id,
        tanggal_izin = input_time,
        alasan = data.alasan,
        judul = data.judul,
        created_at = input_time
    )
    db.add(new_izin)
    db.commit()

    return {
        "message": "Pembuatan izin berhasil!."
    }

UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post('/back-to-office')
async def back_to_office(
    supabase_url: Optional[str] = None,
    bukti_kembali: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id_str: str = Depends(get_auth_user)
):
    if check_libur(db):
        return {"Tidak ada keluar kantor hari ini dikarenakan sedang libur"}

    izin_active = db.query(Izin).filter(
        Izin.user_id == user_id_str,
        Izin.jam_kembali == None
    ).first()

    if not izin_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tidak ada pengajuan izin yang sedang berlangsung untuk Anda."
        )
    
    bukti_url = None
    if bukti_kembali and bukti_kembali.filename:
        ext = os.path.splitext(bukti_kembali.filename)[1]
        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await bukti_kembali.read())
        bukti_url = f"/absen/absen-image/{filename}"
    
    izin_active.jam_kembali = datetime.now(pytz.timezone('Asia/Jakarta'))
    izin_active.bukti_kembali = supabase_url if supabase_url else bukti_url
    izin_active.updated_at = datetime.now(pytz.timezone('Asia/Jakarta'))
         
    db.commit()

    return {
        "message": "Kembali ke kantor berhasil dicatat. Absen Anda telah diperbarui."
    }