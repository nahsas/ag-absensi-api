from datetime import datetime, time, timedelta
import datetime as dt
import os
from typing import Optional
from uuid import uuid4
from fastapi import HTTPException, Request, UploadFile, requests, status
from fastapi.params import Depends
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from jwt import exceptions
import pytz
from sqlalchemy.orm import Session

from app.Models.Absen import Absen
from app.Models.RolesSetting import RolesSetting
from app.Models.SettingJam import SettingJam

SECRET_KEY = 'lbnW+pa2RCtZJRduCC1dXBWy5/xB7mrlHuX63+BuKCo='
ALGORITHM = "HS256"

class OptionalHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            r = await super().__call__(request)
            token = r.credentials
        except HTTPException as ex:
            assert ex.status_code == status.HTTP_403_FORBIDDEN, ex
            token = None
        return token

oauth_scheme = OptionalHTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[dt.timedelta] = None):
    # Salinan data untuk diolah
    to_encode = data.copy()
    
    # Menentukan waktu kadaluwarsa token
    if expires_delta:
        expire = dt.datetime.now(pytz.timezone('Asia/Jakarta')) + expires_delta
    else:
        # Default kadaluwarsa 15 menit
        expire = dt.datetime.now(pytz.timezone('Asia/Jakarta')) + dt.timedelta(minutes=15)
        
    to_encode.update({"exp": expire})
    
    # Membuat token JWT dengan key dan algoritma yang sudah ditentukan
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        id: str = payload.get("sub")
        if id is None:
            raise credentials_exception
            
        return id
        
    except JWTError:
        raise credentials_exception
    
def get_auth_user(token:str = Depends(oauth_scheme)):
    credential_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token expired")
    try:
        if token:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],options={
                "verify_exp":True
            })
            id = payload.get('sub')
            if id is None:
                print("oawk")
            return id
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token not provided")
    except BaseException:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jwt not valid")

# Direktori untuk menyimpan file bukti
UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def add_absen(
    user_id: str, 
    bukti: Optional[UploadFile], 
    keterangan: str,
    point: int,
    tanggal_absen: datetime, 
    db: Session
) -> bool:
    """Menambahkan entri absensi ke database."""
    bukti_url = None
    if bukti and bukti.filename:
        ext = os.path.splitext(bukti.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await bukti.read())
        bukti_url = f"/absen/absen-image/{filename}"

    new_absen = Absen(
        user_id=user_id,
        keterangan=keterangan,
        bukti=bukti_url,
        point=point,
        tanggal_absen=tanggal_absen,
        show=True
    )
    db.add(new_absen)
    db.commit()
    db.refresh(new_absen)
    return True

async def input_izin(
    user_id: str, 
    bukti: Optional[UploadFile], 
    keterangan: str,
    tanggal_absen: datetime, 
    db: Session
) -> bool:
    """Menambahkan entri absensi ke database."""
    bukti_url = None
    if bukti and bukti.filename:
        ext = os.path.splitext(bukti.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(await bukti.read())
        bukti_url = f"/absen/absen-image/{filename}"

    new_absen = Absen(
        user_id=user_id,
        keterangan=keterangan,
        bukti=bukti_url,
        tanggal_absen=tanggal_absen,
        show=False
    )
    db.add(new_absen)
    db.commit()
    db.refresh(new_absen)
    return True

def calculate_point(role_id: str, jam_id: str, absen_time: datetime.time, db: Session) -> int:
    """Menghitung poin berdasarkan aturan role dan jam absensi."""
    
    # Dapatkan semua aturan yang relevan dari RolesSetting untuk role dan jam tertentu
    aturan_list = db.query(RolesSetting).filter(
        RolesSetting.roles_id == role_id,
        RolesSetting.jam_id == jam_id
    ).order_by(RolesSetting.value).all()
    # Mengurutkan berdasarkan `value` akan membantu dalam kasus aturan yang tumpang tindih

    if not aturan_list:
        return 0  # Mengembalikan 0 jika tidak ada aturan yang cocok

    # Dapatkan jam ideal dari SettingJam
    ideal_jam = db.query(SettingJam).get(jam_id).jam
    
    # Hitung selisih waktu dalam menit.
    # Selisih negatif = datang lebih awal
    # Selisih positif = datang terlambat
    ideal_dt = datetime.combine(datetime.today(), ideal_jam)
    absen_dt = datetime.combine(datetime.today(), absen_time)
    diff_minutes = (absen_dt - ideal_dt).total_seconds() / 60

    # Iterasi setiap aturan untuk menemukan yang paling cocok
    # Jika ada beberapa aturan yang cocok, aturan yang terakhir (tergantung urutan) akan mengalahkan yang lain
    final_point = 0
    for aturan in aturan_list:
        if aturan.operator == '=' and diff_minutes == aturan.value:
            final_point = aturan.point
        elif aturan.operator == '>' and diff_minutes > aturan.value:
            final_point = aturan.point
        elif aturan.operator == '<' and diff_minutes < aturan.value:
            final_point = aturan.point
        elif aturan.operator == '>=' and diff_minutes >= aturan.value:
            final_point = aturan.point
        elif aturan.operator == '<=' and diff_minutes <= aturan.value:
            final_point = aturan.point
            
    return final_point

def is_within_absen_time(current_time: datetime.time, jam_absen_rule: SettingJam) -> bool:
    """Memeriksa apakah waktu sekarang berada dalam rentang waktu absensi."""
    return jam_absen_rule.jam <= current_time <= jam_absen_rule.batas_jam