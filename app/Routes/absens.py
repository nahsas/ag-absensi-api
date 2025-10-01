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
from app.Core.GeminiService import compare_image
from app.Models.Absen import Absen
from app.Models.Izin import Izin
from app.Models.RolesSetting import RolesSetting
from app.Models.Sakit import Sakit
from app.Models.Setting import Setting
from app.Models.SettingJam import SettingJam

from sqlalchemy import func

from pydantic import BaseModel, Field

from app.Models.User import HasDinasLuar, User, DinasLuar
from app.Models.UserLembur import Lembur, UserLembur

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
    tipe: Optional[str]
    keterangan: str
    bukti: Union[str, None]
    tanggal_absen: datetime
    point: int

class GetStatusResponse(BaseModel):
    posisi_perusahaan: str
    point_total: int
    isDinasLuar: bool
    isIzin: bool
    data: dict[str, list]

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
    summary="Mendapatkan status absensi harian",
    description="Endpoint untuk mendapatkan status absensi pengguna pada hari ini, termasuk total poin yang telah dikumpulkan."
)
def get_status(db: Session = Depends(get_db), user_id = Depends(get_auth_user)):
        now_date = datetime.now(pytz.timezone('Asia/Jakarta')).date()
        user = db.query(User).where(User.id == user_id).first()

        if not user:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="User not found")

        is_lembur = db.query(UserLembur).join(Lembur).options(joinedload(UserLembur.lembur)).where(UserLembur.user_id == user_id).where(Lembur.start_date <= now_date).where(now_date <= Lembur.end_date).first()
        is_dinas_luar = db.query(DinasLuar).join(HasDinasLuar).join(User).options(joinedload(DinasLuar.has_dinas_luar).joinedload(HasDinasLuar.user)).where(HasDinasLuar.user_id == user_id).where(DinasLuar.tanggal_mulai <= now_date).where(now_date <= DinasLuar.tanggal_selesai).where(DinasLuar.approved == True).first()
        is_izin = False

        total_point = db.query(func.sum(Absen.point)).filter(
            Absen.user_id == user.id,
        ).scalar() or 0

        absen_pagi = db.query(Absen).filter(Absen.user_id == user_id, Absen.pagi != None).where(Absen.keterangan=='hadir').where(datetime.fromisoformat(f"{now_date}T00:00:00") <= Absen.created_at).where(Absen.created_at <= datetime.fromisoformat(f"{now_date}T23:59:59")).first()
        absen_pualng = db.query(Absen).filter(Absen.user_id == user_id, Absen.pulang != None).where(Absen.keterangan=='hadir').where(datetime.fromisoformat(f"{now_date}T00:00:00") <= Absen.created_at).where(Absen.created_at <= datetime.fromisoformat(f"{now_date}T23:59:59")).first()
        is_absent = db.query(Absen).filter(Absen.user_id == user_id).where(Absen.keterangan=='tanpa_keterangan').where(datetime.fromisoformat(f"{now_date}T00:00:00") <= Absen.created_at).where(Absen.created_at <= datetime.fromisoformat(f"{now_date}T23:59:59")).first()
        result = {
            "pagi": None if not absen_pagi else {
                "id":absen_pagi.id,
                "bukti": absen_pagi.bukti_pagi,
                "user_id": absen_pagi.user_id,
                "tanggal_absen": absen_pagi.pagi,
            },
        }

        izin_active = db.query(Izin).filter(Izin.user_id == user_id, Izin.jam_kembali == None).first()
        if izin_active :
            is_izin = True

        now = datetime.now(pytz.timezone('Asia/Jakarta'))
        main_button_text = "Anda Belum absen pagi"
        if result['pagi']: main_button_text = "Anda sudah absen pagi"
        if (is_lembur and result['pagi'] and not now.weekday() != 5) or (is_lembur and now.weekday() == 5): main_button_text = "Hari ini anda di tugaskan lembur"
        if is_absent: main_button_text = "Hari ini anda di anggap alpha"
        if absen_pualng: main_button_text = f"Terimakasih telah bekerja selama ({absen_pualng.lama_bekerja})"
        if is_dinas_luar: main_button_text = "Anda sedang dalam dinas luar"
        if is_izin: main_button_text = "Sedang ada izin yang berjalan"
        if check_libur(db): main_button_text = "Tidak ada absen hari ini, sedang libur"

        return {
            "posisi_perusahaan": user.position,
            "point_total": total_point,
            "isDinasLuar": True if is_dinas_luar else False,
            "isIzin": is_izin,
            "isLembur": True if is_lembur else False,
            "isLibur": check_libur(db),
            "main_button_text": main_button_text,
            "data": result
        }

@router.get(
    '/get-data',
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
    absens_query = db.query(Absen).filter(Absen.user_id == auth_user)
    total_data = absens_query.count()
    max_page = (total_data + limit - 1) // limit
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page and limit must be positive integers.")
    if start_date:
        absens_query = absens_query.filter(Absen.created_at >= start_date)
    if end_date:
        absens_query = absens_query.filter(Absen.created_at <= (end_date + timedelta(days=1)))
    if page > max_page and total_data > 0:
        raise HTTPException(status_code=404, detail="Page not available.")
    offset = (page - 1) * limit

    datas = absens_query.order_by(Absen.created_at.desc()).offset(offset).limit(limit).all()

    res = []
    for data in datas:
        if data.keterangan == 'tanpa_keterangan':
            res.append({
                "id": data.id,
                "tipe": 'tanpa_keterangan',
                "keterangan": "tanpa_keterangan",
                "bukti": None,
                "tanggal_absen": data.created_at,
                "point":0,
            })

        if data.keterangan == 'keluar_kantor':
            izin = db.query(Izin).where(Izin.absen_id == data.id).first()

            res.append({
                "id": data.id,
                "tipe": izin.judul,
                "keterangan": "izin",
                "bukti": izin.bukti_kembali,
                "tanggal_absen": data.created_at,
                "point":0,
            })

        if data.keterangan == 'izin':
            izin = db.query(Sakit).where(Sakit.absen_id == data.id).first()

            res.append({
                "id": data.id,
                "tipe": izin.alasan,
                "keterangan": "sakit",
                "sakit_approve": izin.approved if izin else None,
                "bukti": izin.bukti_sakit,
                "tanggal_absen": data.created_at,
                "point":0,
            })


        if data.pagi:
            res.append({
                "id": data.id,
                "tipe": "Pagi",
                "keterangan": "pagi",
                "bukti": data.bukti_pagi,
                "tanggal_absen": data.pagi,
                "point":data.point,
            })
        if data.istirahat:
            res.append({
                "id": data.id,
                "tipe": "Istirahat",
                "keterangan": "istirahat",
                "bukti": data.bukti_istirahat,
                "tanggal_absen": data.istirahat,
                "point":0,
            })
        if data.kembali_kerja:
            res.append({
                "id": data.id,
                "tipe": "Kembali Kerja",
                "keterangan": "kembali kantor",
                "bukti": data.bukti_kembali_kerja,
                "tanggal_absen": data.kembali_kerja,
                "point":0,
            })
        if data.pulang:
            res.append({
                "id": data.id,
                "tipe": "Pulang",
                "keterangan": "pulang",
                "bukti": data.bukti_pulang,
                "tanggal_absen": data.pulang,
                "point":0,
            })
        if data.mulai_lembur:
            res.append({
                "id": data.id,
                "tipe": "Mulai Lembur",
                "keterangan": "mulai_lembur",
                "bukti": data.bukti_lembur_mulai,
                "tanggal_absen": data.mulai_lembur,
                "point":0,
            })
        if data.selesai_lembur:
            res.append({
                "id": data.id,
                "tipe": "Selesai Lembur",
                "keterangan": "selesai_lembur",
                "bukti": data.bukti_lembur_selesai,
                "tanggal_absen": data.selesai_lembur,
                "point":0,
            })

    return {
        "page": page,
        "max_page": max_page,
        "total_data": total_data,
        "data": res
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
    summary="Melakukan absensi",
    description="Endpoint untuk melakukan absensi (masuk, istirahat, kembali, atau pulang) sesuai dengan waktu saat ini. Bukti foto dapat diunggah."
)
def absen_masuk(
    input_time: Optional[datetime] = None, 
    supabase_url: Optional[str] = None, 
    bukti: UploadFile = File(None), 
    db: Session = Depends(get_db), 
    user_id: str = Depends(get_auth_user)
):
    is_lembur = db.query(UserLembur).join(Lembur).options(joinedload(UserLembur.lembur)).where(UserLembur.user_id == user_id).where(Lembur.start_date <= datetime.now(pytz.timezone('Asia/Jakarta')).date()).where(datetime.now(pytz.timezone('Asia/Jakarta')).date() <= Lembur.end_date).first()

    if check_libur(db) and not is_lembur:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Tidak ada absen hari ini, dikarenakan libur")

    input_time = datetime.now(pytz.timezone('Asia/Jakarta'))
    start_of_the_day = datetime.fromisoformat(f"{input_time.date()}T00:00:00")
    end_of_the_day = datetime.fromisoformat(f"{input_time.date()}T23:59:59")
    check_izin_active = db.query(Izin).where(Izin.user_id == user_id).where(Izin.jam_kembali == None).first()

    today_absen = db.query(Absen).where(Absen.user_id==user_id).where(Absen.keterangan == 'hadir').where(start_of_the_day <= Absen.created_at).where(Absen.created_at <= end_of_the_day).first()
    yesterday_absen = db.query(Absen).where(Absen.user_id==user_id).where(Absen.keterangan == 'hadir').where((start_of_the_day - timedelta(days=1)) <= Absen.created_at).where(Absen.created_at <= start_of_the_day).first()

    if check_izin_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Anda sedang izin, mohon kembali ke kantor terlebih dahulu")        

    if db.query(Absen).filter(Absen.user_id == user_id).where(Absen.keterangan=='tanpa_keterangan').where(start_of_the_day <= Absen.created_at).where(Absen.created_at <= end_of_the_day).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Tidak ada absen lagi")

    if not today_absen and not check_libur(db):
        user = db.query(User).where(User.id == user_id).first()
        compared_image = compare_image(supabase_url, user.photo_profile)
        if not compared_image['status']:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Wajah tidak sama dengan yang terdata di database")

        new_absen = Absen(
            id=str(uuid.uuid4()),
            user_id=user_id,
            keterangan="Hadir",
            pagi=input_time,
            bukti_pagi=supabase_url,
            point=calculate_point(user_id, input_time.time(), db),
            created_at=input_time
        )

        db.add(new_absen)
        db.commit()

        return {
            "message": f"Absensi pagi berhasil!",
            "tipe_absen": "pagi",
            "point_didapat": 0
        }
    
    if today_absen and not check_libur(db):
        if today_absen.istirahat == None and input_time.weekday() != 5:        
            today_absen.istirahat = input_time
            today_absen.bukti_istirahat = supabase_url
            today_absen.updated_at = input_time

            db.commit()

            return {
                "message": f"Absensi istirahat berhasil!",
                "tipe_absen": "Istirahat",
                "point_didapat": 0
            }

        if today_absen.kembali_kerja == None and input_time.weekday() != 5:
            today_absen.kembali_kerja = input_time
            today_absen.bukti_kembali_kerja = supabase_url
            today_absen.updated_at = input_time

            db.commit()

            return {
                "message": f"Absensi kembali kerja berhasil!",
                "tipe_absen": "kembali kerja",
                "point_didapat": 0
            }

        if today_absen.pulang == None :
            today_absen.pulang = input_time
            today_absen.bukti_pulang = supabase_url
            today_absen.updated_at = input_time

            db.commit()

            return {
                "message": f"Absensi pulang berhasil!",
                "tipe_absen": "Pulang",
                "point_didapat": 0
            }

        if today_absen.mulai_lembur == None and is_lembur and today_absen.pulang:
            today_absen.mulai_lembur = input_time
            today_absen.bukti_lembur_mulai = supabase_url
            today_absen.updated_at = input_time

            db.commit()

            return {
                "message": f"Absensi mulai lembur berhasil!",
                "tipe_absen": "Mulai Lembur",
                "point_didapat": 0
            }

        if today_absen.selesai_lembur == None and is_lembur and today_absen.mulai_lembur:
            today_absen.selesai_lembur = input_time
            today_absen.bukti_lembur_selesai = supabase_url
            today_absen.updated_at = input_time

            db.commit()

            return {
                "message": f"Absensi selesai lembur berhasil!",
                "tipe_absen": "Selesai Lembur",
                "point_didapat": 0
            }
    
    if check_libur(db) and is_lembur and not today_absen:
        new_absen = Absen(
            id=str(uuid.uuid4()),
            user_id=user_id,
            keterangan="Hadir",
            mulai_lembur=input_time,
            bukti_lembur_mulai=supabase_url,
            created_at=input_time
        )

        db.add(new_absen)
        db.commit()

        return {
            "message": f"Absensi pagi berhasil!",
            "tipe_absen": "pagi",
            "point_didapat": 0
        }

    if not today_absen.selesai_lembur and is_lembur and today_absen.mulai_lembur and check_libur(db):
        today_absen.selesai_lembur = input_time
        today_absen.bukti_lembur_selesai = supabase_url
        today_absen.updated_at = input_time

        db.commit()

        return {
            "message": f"Absensi selesai lembur berhasil!",
            "tipe_absen": "Selesai Lembur",
            "point_didapat": 0
        }

    raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Tidak ada absen lagi")

@router.get('/absen_detail/{absen_id}')
def get_absen_detail(absen_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    absen = db.query(Absen).where(Absen.id == absen_id, Absen.user_id == user_id).first()

    if not absen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Absen tidak ditemukan")

    return absen