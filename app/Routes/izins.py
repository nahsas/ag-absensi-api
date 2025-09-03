from datetime import datetime
import os
from typing import Optional, Union
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from app.Core.Database import get_db
from app.Core.Essential import get_auth_user
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
    user_id: int = Depends(get_auth_user)
):    
    user_id = user_id.encode('utf-8');

    try:
        # Pengecekan input_time (jika diperlukan)
        input_time = datetime.now() if data.input is None else datetime.fromisoformat(data.input)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format datetime tidak valid. Gunakan format ISO 8601 (contoh: '2025-08-23T10:00:00')."
        )
    
    # Dapatkan user lengkap dengan relasinya
    user = db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    if not user or not user.role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User atau role tidak ditemukan.")

    # Cek apakah user sudah memiliki status izin yang belum selesai
    existing_izin = db.query(Izin).filter(
        Izin.user_id == user.id,
        Izin.jam_kembali == None,
        Izin.approved == False # Hanya cek izin yang belum disetujui atau ditolak
    ).first()

    if existing_izin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anda sudah memiliki pengajuan izin yang sedang diproses. Silakan tunggu hingga disetujui."
        )

    # Simpan file bukti ke storage
    # Implementasi ini bergantung pada kebutuhan Anda (contoh sederhana)
    # file_path = f"path/to/your/storage/bukti_{user.id}_{datetime.now().isoformat()}.jpg"
    # with open(file_path, "wb") as f:
    #     f.write(bukti.file.read())

    # Buat entri baru di tabel Absen
    new_absen = Absen(
        id=uuid.uuid4(),
        user_id=user.id,
        keterangan="izin",
        point=0, # point akan dihitung saat kembali
        tanggal_absen=input_time,
        show=True
    )
    db.add(new_absen)
    db.flush() # Ambil ID dari absen yang baru dibuat

    # Buat entri baru di tabel Izins
    new_izin = Izin(
        id=uuid.uuid4(),
        user_id=user.id,
        absen_id=new_absen.id,
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
    user_id: int = Depends(get_auth_user)
):
    user_id = user_id.encode('utf-8');
    
    # Cari izin yang sedang berlangsung untuk user ini
    izin_active = db.query(Izin).filter(
        Izin.user_id == user_id,
        Izin.jam_kembali.is_(None)
    ).first()

    if not izin_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tidak ada pengajuan izin yang sedang berlangsung untuk Anda."
        )
    
    bukti_url = None
    if bukti_kembali and bukti_kembali.filename:
        ext = os.path.splitext(bukti_kembali.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await bukti_kembali.read())
        bukti_url = f"/absen/absen-image/{filename}"
    
    # Update data izin dengan data kembali
    izin_active.jam_kembali = datetime.now()
    izin_active.bukti_kembali = bukti_url
    
    # Hitung durasi izin
    absen_izin = db.query(Absen).filter(Absen.id == izin_active.absen_id).first()
    if absen_izin:
        durasi_izin = izin_active.jam_kembali - absen_izin.tanggal_absen
        izin_active.keluar_selama = durasi_izin.seconds // 60 # dalam menit


    db.commit()

    return {
        "message": "Kembali ke kantor berhasil dicatat. Absen Anda telah diperbarui."
    }