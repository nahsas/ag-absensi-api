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
from app.Models.Setting import Setting
from app.Models.SettingJam import SettingJam
from app.Models.User import User

SECRET_KEY = 'lbnW+pa2RCtZJRduCC1dXBWy5/xB7mrlHuX63+BuKCo='
ALGORITHM = "HS256"
# Direktori untuk menyimpan file bukti
UPLOAD_DIR = "uploads/absen_bukti"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

def check_libur(db:Session) -> bool:
    try:
        is_libur = db.query(Setting).where(Setting.name == 'Libur').first().value
        return True if is_libur == 'true' else False
    except Exception:
        return HTTPException(status.HTTP_400_BAD_REQUEST, "'Libur' Tidak ada di setting database")

def calculate_point(user: str, absen_time: datetime.time, db: Session) -> int:
    user_auth = db.query(User).where(User.id == user).first()
    role_setting = db.query(RolesSetting).where(RolesSetting.roles_id == user_auth.roles_id).order_by(RolesSetting.point).all()

    if not role_setting:
        return 0
    
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

def is_within_absen_time(current_time: datetime.time, jam_absen_rule: SettingJam) -> bool:
    """Memeriksa apakah waktu sekarang berada dalam rentang waktu absensi."""
    return jam_absen_rule.jam <= current_time <= jam_absen_rule.batas_jam