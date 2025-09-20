from datetime import datetime, time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
import pytz
from sqlalchemy.orm import Session, joinedload
from app.Core import Env
from app.Core.Database import get_db
from app.Core.Essential import check_libur, get_auth_user
import geocoder as gc
import math
from pydantic import BaseModel, Field

from app.Models.Absen import Absen
from app.Models.RolesSetting import RolesSetting
from app.Models.Setting import Setting
from app.Models.SettingJam import SettingJam
from app.Models.User import User
from app.Models.UserLembur import Lembur, UserLembur

# Definisikan Pydantic model untuk respons sukses
class GetDistanceResponse(BaseModel):
    status: bool
    detail: str
    jarak: str

# Definisikan Pydantic model untuk respons error
class DistanceError(BaseModel):
    detail: str
    
maximal_jarak_login_m = 20

router = APIRouter()

@router.get(
    '/get-distance',
    summary="Menghitung jarak dari kantor",
    description="Endpoint untuk menghitung jarak antara lokasi pengguna dan lokasi kantor. Digunakan untuk validasi absensi.",
    response_model=GetDistanceResponse,
    responses={
        400: {
            "model": DistanceError,
            "description": "Respons jika jarak melebihi batas yang diizinkan."
        }
    }
)
def get_distance(
    lat: float, 
    lon: float, 
    batas_jarak: int = maximal_jarak_login_m, 
    db: Session = Depends(get_db)
):
    lat_db = float(db.query(Setting).where(Setting.name == 'Lat Perusahaan').first().value)
    lon_db = float(db.query(Setting).where(Setting.name == 'Lon Perusahaan').first().value)
    batas_jarak = int(db.query(Setting).where(Setting.name == 'Jarak dari kantor').first().value)

    coords = {f"lat":lat_db, "lon":lon_db}

    jarak = haversine(coords['lat'], coords['lon'], lat, lon)

    if jarak > batas_jarak:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 
            detail=f"Terlalu jauh dari kantor untuk memproses data, anda berada {(jarak - batas_jarak):.2f} meter dari luar kantor"
        )
    return {
        "status": True,
        "detail": "Anda berada dalam jangkauan kantor",
        "jarak": f"{jarak:.2f} meter"
    }

def haversine(lat1, lon1, lat2, lon2):
    """
    Menghitung jarak Haversine antara dua titik koordinat (latitude, longitude)
    dalam meter.
    """
    R = 6371000

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1) # Perbaikan: Gunakan lon1
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2) # Perbaikan: Gunakan lon2

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

@router.get('/time_setting')
def getTimeSetting(date_simulation:Optional[datetime] = None, db:Session = Depends(get_db), user_id = Depends(get_auth_user)):
    if not date_simulation:
        date_simulation = datetime.now().date()
    is_lembur = db.query(UserLembur).join(Lembur).options(joinedload(UserLembur.lembur)).where(UserLembur.user_id == user_id).where(Lembur.start_date <= datetime.now(pytz.timezone('Asia/Jakarta')).date()).where(datetime.now(pytz.timezone('Asia/Jakarta')).date() <= Lembur.end_date).first()

    query_res = db.query(SettingJam).order_by(SettingJam.jam)
    jam_absen_pulang_bawah = query_res.where(SettingJam.nama_jam == 'Pulang').first().jam
    jam_absen_pulang_atas = query_res.where(SettingJam.nama_jam == 'Pulang').first().batas_jam
    check_already_absen_pulang = db.query(Absen).where(Absen.keterangan == 'Pulang').where(Absen.user_id==user_id).where(datetime.combine(datetime.now(pytz.timezone('Asia/Jakarta')).date(), jam_absen_pulang_bawah) <= Absen.tanggal_absen).where(Absen.tanggal_absen <= datetime.combine(datetime.now(pytz.timezone('Asia/Jakarta')).date(), jam_absen_pulang_atas)).first()
    absen_mulai_lembur = db.query(Absen).where(Absen.keterangan == "lembur").where(Absen.lembur_start != None).where(Absen.lembur_end == None).first()
    query_res = query_res.all()
    res = []


    if check_libur(db) and not is_lembur:
        for data in query_res:
            jam = time.fromisoformat(str(data.jam)).hour
            menit = time.fromisoformat(str(data.jam)).minute
            jam_akhir = time.fromisoformat(str(data.batas_jam)).hour
            menit_akhir = time.fromisoformat(str(data.batas_jam)).minute

            res.append({
                "nama":data.nama_jam,
                "jam_awal":{
                    "jam":0,
                    "menit":0
                },
                "jam_akhir":{
                    "jam":0,
                    "menit":0
                }
            })

        return res

    if (check_already_absen_pulang and is_lembur and not absen_mulai_lembur) or (check_libur(db) and is_lembur and not absen_mulai_lembur):
        for data in query_res:
            jam = time.fromisoformat(str(data.jam)).hour
            menit = time.fromisoformat(str(data.jam)).minute

            res.append({
                "nama":"Mulai Lembur" if data.nama_jam == "Pulang" else data.nama_jam,
                "jam_awal":{
                    "jam":0,
                    "menit":0
                },
                "jam_akhir":{
                    "jam":23,
                    "menit":59
                }
            })
        
        return res

    if (check_already_absen_pulang and is_lembur and absen_mulai_lembur) or (check_libur(db) and is_lembur and absen_mulai_lembur):
        for data in query_res:
            jam = time.fromisoformat(str(data.jam)).hour
            menit = time.fromisoformat(str(data.jam)).minute

            res.append({
                "nama":"Selesai Lembur" if data.nama_jam == "Pulang" else data.nama_jam,
                "jam_awal":{
                    "jam":0,
                    "menit":0
                },
                "jam_akhir":{
                    "jam":23,
                    "menit":59
                }
            })
        
        return res

    for data in query_res:
        jam = time.fromisoformat(str(data.jam)).hour
        menit = time.fromisoformat(str(data.jam)).minute
        jam_akhir = time.fromisoformat(str(data.batas_jam)).hour
        menit_akhir = time.fromisoformat(str(data.batas_jam)).minute

        res.append({
            "nama":data.nama_jam,
            "jam_awal":{
                "jam":jam,
                "menit":menit
            },
            "jam_akhir":{
                "jam":jam_akhir,
                "menit":menit_akhir
            }
        })

    return res


@router.get('/get_setting')
def getSetting(db: Session = Depends(get_db)):
    res = db.query(Setting).all()
    return res

@router.get('/get_statistic')
def getStatistic(db: Session = Depends(get_db), user = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user).first()

    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User tidak ditemukan")

    res = []

    datas = {
        "absen_plus_this_month": sum([item.point for item in db.query(Absen).where(Absen.user_id == user.id).where(Absen.point > 0).where(Absen.tanggal_absen.between(datetime.now(pytz.timezone('Asia/Jakarta')).replace(day=1), datetime.now(pytz.timezone('Asia/Jakarta')))).all()]),
        "absen_minus_this_month": sum([item.point for item in db.query(Absen).where(Absen.user_id == user.id).where(Absen.point < 0).where(Absen.tanggal_absen.between(datetime.now(pytz.timezone('Asia/Jakarta')).replace(day=1), datetime.now(pytz.timezone('Asia/Jakarta')))).all()]),
        "absen_plus_month_before": sum([item.point for item in db.query(Absen).where(Absen.user_id == user.id).where(Absen.point > 0).where(Absen.tanggal_absen < datetime.now(pytz.timezone('Asia/Jakarta')).replace(day=1)).all()]),
        "absen_minus_month_before": sum([item.point for item in db.query(Absen).where(Absen.user_id == user.id).where(Absen.point < 0).where(Absen.tanggal_absen < datetime.now(pytz.timezone('Asia/Jakarta')).replace(day=1)).all()])
    }

    res = {
        "absen_plus_this_month":{
            "point":datas["absen_plus_this_month"]
        },
        "absen_minus_this_month":{
            "point":datas["absen_minus_this_month"]
        },
        "absen_plus_month_before":{
            "point":datas["absen_plus_month_before"]
        },
        "absen_minus_month_before":{
            "point":datas["absen_minus_month_before"]
        }
    }

    return res