from datetime import datetime, time
from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
from app.Core import Env
from app.Core.Database import get_db
from app.Core.Essential import get_auth_user
import geocoder as gc
import math
from pydantic import BaseModel, Field

from app.Models.RolesSetting import RolesSetting
from app.Models.Setting import Setting
from app.Models.SettingJam import SettingJam
from app.Models.User import User

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
    coords = {f"lat":-2.7405128, "lon":107.6496313}

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
def getTimeSetting(db:Session = Depends(get_db)):
    query_res = db.query(SettingJam).order_by(SettingJam.jam).all()

    res = []
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
        });

    return res


@router.get('/get_setting')
def getSetting(db: Session = Depends(get_db)):
    res = db.query(Setting).all()
    return res


@router.get('/develop')
def point(absen_time:time,db:Session = Depends(get_db), user:str = Depends(get_auth_user)):
    user_auth = db.query(User).where(User.id == user).first()
    role_setting = db.query(RolesSetting).where(RolesSetting.roles_id == user_auth.roles_id).order_by(RolesSetting.point).all()

    if not role_setting:
        return 0  # Mengembalikan 0 jika tidak ada aturan yang cocok
    
    # Hitung selisih waktu dalam menit.
    # Selisih negatif = datang lebih awal
    # Selisih positif = datang terlambat

    # Iterasi setiap aturan untuk menemukan yang paling cocok
    # Jika ada beberapa aturan yang cocok, aturan yang terakhir (tergantung urutan) akan mengalahkan yang lain
    final_point = 0
    for aturan in role_setting:
        aturan_dt = datetime.combine(datetime.today(), time.fromisoformat(str(aturan.value)).replace(second=0,microsecond=0))
        absen_dt = datetime.combine(datetime.today(), absen_time.replace(second=0,microsecond=0))
        print(aturan_dt)
        print(absen_dt)
        diff_minutes = (absen_dt - aturan_dt).total_seconds() / 60
        if aturan.operator == '=' and absen_dt == aturan_dt:
            final_point = aturan.point
            break
        elif aturan.operator == '>' and absen_dt > aturan_dt:
            final_point = aturan.point
            break
        elif aturan.operator == '<' and absen_dt < aturan_dt:
            final_point = aturan.point
            break
        elif aturan.operator == '>=' and absen_dt >= aturan_dt:
            final_point = aturan.point
            break
        elif aturan.operator == '<=' and absen_dt <= aturan_dt:
            final_point = aturan.point
            break
            
    return final_point