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
    user_id_str: str = Depends(get_auth_user)
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
    
    # Dapatkan user lengkap dengan relasinya
    # Pastikan perbandingan menggunakan string atau UUID jika model User.id adalah UUID
    user = db.query(User).options(joinedload(User.role)).filter(User.id == user_id_str).first()
    if not user or not user.role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User atau role tidak ditemukan.")

    # Cek apakah user sudah memiliki status izin yang belum selesai
    # Perbandingan Izin.user_id dengan user.id, keduanya harus konsisten
    existing_izin = db.query(Izin).filter(
        Izin.user_id == user_id_str, # Menggunakan string user_id_str
        Izin.jam_kembali == None,
        Izin.approved == None # Menggunakan None untuk izin yang belum disetujui atau ditolak
    ).first()

    if existing_izin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anda sudah memiliki pengajuan izin yang sedang diproses. Silakan tunggu hingga disetujui."
        )

    # Buat entri baru di tabel Absen
    new_absen = Absen(
        id=str(uuid.uuid4()), # Pastikan ID dibuat sebagai string
        user_id=user_id_str, # Menggunakan string user_id_str
        keterangan="izin",
        point=0,
        tanggal_absen=input_time,
        show=True
    )
    db.add(new_absen)
    db.flush()

    # Buat entri baru di tabel Izins
    new_izin = Izin(
        id=str(uuid.uuid4()), # Pastikan ID dibuat sebagai string
        user_id=user_id_str, # Menggunakan string user_id_str
        absen_id=new_absen.id, # new_absen.id sudah berupa string
        alasan=data.alasan,
        jam_kembali=None,
        bukti_kembali=None,
        keluar_selama=0,
        judul=data.judul,
        approved=None,
    )
    db.add(new_izin)
    db.commit()

    return {
        "message": "Pembuatan izin berhasil! Admin akan segera memprosesnya."
    }

UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post('/back-to-office')
async def back_to_office(
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
    izin_active.bukti_kembali = bukti_url
    
    absen_izin = db.query(Absen).filter(Absen.id == izin_active.absen_id).first()
    if absen_izin:
        jam_kembali_dt = izin_active.jam_kembali
        tanggal_absen_dt = absen_izin.tanggal_absen
        if isinstance(jam_kembali_dt, str):
            jam_kembali_dt = datetime.fromisoformat(jam_kembali_dt)
        if isinstance(tanggal_absen_dt, str):
            tanggal_absen_dt = datetime.fromisoformat(tanggal_absen_dt)
        # Ensure both datetimes are timezone-aware
        tz = pytz.timezone('Asia/Jakarta')
        if jam_kembali_dt.tzinfo is None:
            jam_kembali_dt = tz.localize(jam_kembali_dt)
        if tanggal_absen_dt.tzinfo is None:
            tanggal_absen_dt = tz.localize(tanggal_absen_dt)
        durasi_izin = jam_kembali_dt - tanggal_absen_dt
        izin_active.keluar_selama = int(durasi_izin.total_seconds() // 60)
    
    db.commit()

    return {
        "message": "Kembali ke kantor berhasil dicatat. Absen Anda telah diperbarui."
    }