from typing import Optional, Union
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
import pytz
from sqlalchemy import Date, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, time
from fastapi import File, UploadFile, Request
import os
from uuid import UUID, uuid4

from app.Core.Database import get_db
from app.Core.Essential import add_absen, calculate_point, check_libur, get_auth_user
from app.Models.Absen import Absen
from app.Models.Izin import Izin
from app.Models.RolesSetting import RolesSetting
from app.Models.Sakit import Sakit
from app.Models.Setting import Setting
from app.Models.SettingJam import SettingJam
from app.Models.User import User

from sqlalchemy import func

# Impor Pydantic models untuk request body dan response
from pydantic import BaseModel, Field

# Definisikan Pydantic models untuk respons
class AbsenStatusResponse(BaseModel):
    id: UUID
    user_id: UUID
    keterangan: str
    bukti: Optional[str]
    point: int
    tanggal_absen: datetime
    show: bool

class AbsenDataResponse(BaseModel):
    id: UUID
    tipe: str
    keterangan: str
    bukti: Optional[str]
    sakit_approve: Optional[bool]
    tanggal_absen: datetime
    point: int

class GetStatusResponse(BaseModel):
    posisi_perusahaan: str
    point_total: int
    isDinasLuar: bool
    isIzin: bool
    data: dict[str, Optional[AbsenStatusResponse]]

class GetDataResponse(BaseModel):
    page: int
    max_page: int
    total_data: int
    data: list[AbsenDataResponse]

class SetAbsenResponse(BaseModel):
    message: str
    tipe_absen: str
    point_didapat: int

router = APIRouter()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, 'uploads',"absen_bukti")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get(
    '/status',
    # response_model=GetStatusResponse,
    summary="Mendapatkan status absensi harian",
    description="Endpoint untuk mendapatkan status absensi pengguna pada hari ini, termasuk total poin yang telah dikumpulkan."
)
def get_status(db: Session = Depends(get_db), user_id = Depends(get_auth_user)):
        isIzin = False
        isDinasLuar = False
        today = datetime.now(pytz.timezone('Asia/Jakarta')).date()
        user = db.query(User).where(User.id == user_id).first()

        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User not found")

        total_point = db.query(func.sum(Absen.point)).filter(
            Absen.user_id == user.id,
        ).scalar() or 0

        try:
            jam_masuk = db.query(SettingJam).where(SettingJam.nama_jam == 'Jam masuk').first()
            istirahat = db.query(SettingJam).where(SettingJam.nama_jam == 'Istirahat').first()
            kembali = db.query(SettingJam).where(SettingJam.nama_jam == 'Masuk kembali').first()
            pulang = db.query(SettingJam).where(SettingJam.nama_jam == 'Pulang').first()
        except Exception:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="pastikan 'Jam masuk','Istirahat','Masuk kembali','Pulang' sudah di set di database")

        result = {
            "pagi": db.query(Absen).filter(Absen.user_id == user_id, Absen.tanggal_absen >= f"{datetime.combine(today, jam_masuk.jam)}", Absen.tanggal_absen < f"{datetime.combine(today, jam_masuk.batas_jam)}").where(Absen.keterangan=='hadir').first(),
            "istirahat": db.query(Absen).filter(Absen.user_id == user_id, Absen.tanggal_absen >= f"{datetime.combine(today, istirahat.jam)}", Absen.tanggal_absen < f"{datetime.combine(today, istirahat.batas_jam)}").where(Absen.keterangan=='hadir').first(),
            "kembali": db.query(Absen).filter(Absen.user_id == user_id, Absen.tanggal_absen >= f"{datetime.combine(today, kembali.jam)}", Absen.tanggal_absen < f"{datetime.combine(today, kembali.batas_jam)}").where(Absen.keterangan=='hadir').first(),
            "pulang": db.query(Absen).filter(Absen.user_id == user_id, Absen.tanggal_absen >= f"{datetime.combine(today, pulang.jam)}", Absen.tanggal_absen < f"{datetime.combine(today, pulang.batas_jam)}").where(Absen.keterangan=='hadir').first()
        }

        izin_active = db.query(Izin).filter(Izin.user_id == user_id, Izin.jam_kembali == None).first()
        if izin_active :
            isIzin = True
        
        dinas_luar = db.query(Absen).where(datetime.combine(today, time.fromisoformat("00:00:00")) < Absen.tanggal_absen, Absen.tanggal_absen < datetime.combine(today, time.fromisoformat("23:59:59"))).first()
        if dinas_luar :
            isDinasLuar = True

        return {
            "posisi_perusahaan": user.position,
            "point_total": total_point,
            "isDinasLuar": isDinasLuar,
            "isIzin": isIzin,
            "data": result
        }

@router.get(
    '/get-data',
    response_model=GetDataResponse,
    summary="Mendapatkan riwayat absensi",
    description="Endpoint untuk mendapatkan daftar absensi pengguna dengan dukungan paginasi dan filter tanggal."
)
def get_absens(
    page: int = 1, 
    limit: int = 5, 
    start_date: Union[date, None] = None, 
    end_date: Union[date, None] = None, 
    db: Session = Depends(get_db), 
    auth_user: str = Depends(get_auth_user)
):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page and limit must be positive integers.")

    absens_query = db.query(Absen).filter(Absen.show == True, Absen.user_id == auth_user)
    if start_date:
        absens_query = absens_query.filter(Absen.tanggal_absen >= start_date)
    if end_date:
        absens_query = absens_query.filter(Absen.tanggal_absen <= (end_date + timedelta(days=1)))

    total_data = absens_query.count()
    max_page = (total_data + limit - 1) // limit

    if page > max_page and total_data > 0:
        raise HTTPException(status_code=404, detail="Page not available.")

    offset = (page - 1) * limit
    data = absens_query.order_by(Absen.tanggal_absen.desc()).offset(offset).limit(limit).all()

    try:
        jam_masuk = db.query(SettingJam).where(SettingJam.nama_jam == 'Jam masuk').first()
        istirahat = db.query(SettingJam).where(SettingJam.nama_jam == 'Istirahat').first()
        kembali = db.query(SettingJam).where(SettingJam.nama_jam == 'Masuk kembali').first()
        pulang = db.query(SettingJam).where(SettingJam.nama_jam == 'Pulang').first()
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="pastikan 'Jam masuk','Istirahat','Masuk kembali','Pulang' sudah di set di database")


    result = []
    for absen in data:
        absen_time = absen.tanggal_absen.time()
        tipe = "Unknown"

        sakit_approve = None


        if absen.keterangan == 'izin':
            izin = db.query(Izin).where(Izin.absen_id == absen.id).first()
            tipe = izin.judul if izin is not None else "Izin"
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue

        if absen.keterangan == 'sakit':
            tipe = f"Izin"
            sakit = db.query(Sakit).where(Sakit.absen_id == absen.id).first()
            sakit_approve = sakit.approved if sakit else None            
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue

        if absen.keterangan == 'dinas_luar':
            tipe = 'Dinas Luar'
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue

        if absen.keterangan == 'tanpa_keterangan':
            tipe = "Alpha"
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue

        if absen_time >= pulang.jam:
            tipe = "Pulang"
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue
        elif absen_time >= kembali.jam:
            tipe = "Kembali ke kantor"
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue
        elif absen_time >= istirahat.jam:
            tipe = "Istirahat"
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue
        elif absen_time >= jam_masuk.jam:
            tipe = 'Masuk'
            result.append({"id": absen.id,"tipe": tipe,"keterangan": absen.keterangan,"sakit_approve": sakit_approve,"bukti": absen.bukti,"tanggal_absen": absen.tanggal_absen,"point": absen.point})
            continue

    return {
        "page": page,
        "max_page": max_page,
        "total_data": total_data,
        "data": result
    }

@router.get(
    "/absen-image/{filename}", 
    summary="Mendapatkan gambar bukti absen",
    description="Endpoint untuk menampilkan gambar bukti absen berdasarkan nama berkas.",
    response_class=FileResponse
)
def get_absen_image(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@router.post(
    '/set',
    # response_model=SetAbsenResponse,
    summary="Melakukan absensi",
    description="Endpoint untuk melakukan absensi (masuk, istirahat, kembali, atau pulang) sesuai dengan waktu saat ini. Bukti foto dapat diunggah."
)
async def absen_masuk(
    input_time: Optional[datetime] = None, 
    bukti: UploadFile = File(None), 
    db: Session = Depends(get_db), 
    user_id: str = Depends(get_auth_user)
):
    if check_libur(db):
        return {"Tidak ada absen hari ini dikarenakan sedang libur"}

    input_time = datetime.now(pytz.timezone('Asia/Jakarta'))

    user = db.query(User).options(joinedload(User.role)).get(user_id)
    if not user or not user.role:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User atau role tidak ditemukan.")

    daftar_jam = db.query(SettingJam).order_by(SettingJam.jam).all()
    
    jam_absen_rule = None
    for rule in daftar_jam:
        if rule.jam <= input_time.time() <= rule.batas_jam:
            jam_absen_rule = rule
            break
            
    if not jam_absen_rule: # Periksa ID, bukan objek        
        next_absen_time = None
        for rule in daftar_jam:
            if input_time.time() < rule.jam:
                next_absen_time = rule.jam
                break
        
        detail_msg = "Jam tidak valid untuk melakukan absen."
        if next_absen_time:
            detail_msg += f" Absen berikutnya: {next_absen_time.strftime('%H:%M')}"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=detail_msg)

    already_absent = db.query(Absen).filter(        
        Absen.user_id == user_id,
        Absen.keterangan == 'hadir',
        Absen.tanggal_absen >= datetime.combine(input_time.date(), jam_absen_rule.jam),
        Absen.tanggal_absen <= datetime.combine(input_time.date(), jam_absen_rule.batas_jam)
    ).first()

    if already_absent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            detail=f"Anda sudah melakukan absen {jam_absen_rule.nama_jam}"
        )
    
    point = calculate_point(user.id, input_time.time(), db)
    
    keterangan_absen = "hadir" 

    await add_absen(
        user_id=user_id,
        bukti=bukti,
        keterangan=keterangan_absen,
        point=point,
        tanggal_absen=input_time,
        db=db
    )

    return {
        "message": f"Absensi {jam_absen_rule.nama_jam} berhasil!",
        "tipe_absen": jam_absen_rule.nama_jam,
        "point_didapat": point
    }

@router.get('/absen_detail/{absen_id}')
def get_absen_detail(absen_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    absen = db.query(Absen).where(Absen.id == absen_id, Absen.user_id == user_id).first()

    if not absen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Absen tidak ditemukan")

    return absen