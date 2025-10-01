from datetime import datetime, timedelta
import os
from typing import Optional, Union
from uuid import UUID, uuid4
from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
import pytz
from sqlalchemy.orm import Session
import bcrypt as bc

from app.Core.Database import get_db
from app.Core.Essential import create_access_token, get_auth_user
from app.Models.User import DinasLuar, HasDinasLuar, User
from app.Models.UserLembur import Lembur, UserLembur
from app.Schema import user
from pydantic import BaseModel, Field
from sqlalchemy.orm import joinedload

UPLOAD_DIR = "uploads/profile_picture"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.post(
    '/auth/login',
    summary="Login user",
    description="Endpoint untuk user login menggunakan NIP dan password. Jika berhasil, akan mengembalikan token otentikasi.",
)
def get_users(data: user.LoginUser, db: Session = Depends(get_db)):
    res = db.query(User).where(User.nip == data.nip).first()
    now_date = datetime.now(pytz.timezone('Asia/Jakarta')).date()
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nip tidak terdaftar di sistem")

    if res.password.startswith('$2a$') or res.password.startswith('$2b$'):
        hashed_password = res.password.encode('utf-8')
    else:
        hashed_password = res.password.encode('utf-8').replace(b'$2b$', b'$2y$')
    
    check_password = bc.checkpw(data.password.encode('utf-8'), hashed_password)
    
    if not check_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password salah")

    is_lembur = db.query(UserLembur).join(Lembur).options(joinedload(UserLembur.lembur)).where(UserLembur.user_id == res.id).where(Lembur.start_date <= now_date).where(now_date <= Lembur.end_date).first()
    is_dinas_luar = db.query(DinasLuar).join(HasDinasLuar).join(User).options(joinedload(DinasLuar.has_dinas_luar).joinedload(HasDinasLuar.user)).where(HasDinasLuar.user_id == res.id).where(DinasLuar.tanggal_mulai <= now_date).where(now_date <= DinasLuar.tanggal_selesai).where(DinasLuar.approved == True).first()

    access_token = create_access_token(db,data={"sub": str(res.id)})

    result = {
        "id": res.id,
        "nip": res.nip,
        "role": res.role.name,
        "name": res.name,
        "photo": res.photo_profile,
        "posisi_perusahaan": res.position,
        "isFirstLogin": res.isFirstLogin,
        "is_lembur":True if is_lembur else False,
        "is_dinas_luar": True if is_dinas_luar else False,
        "token": access_token,
    }

    return result

@router.put(
    '/update/password',
    summary="Update password user",
    description="Endpoint untuk memperbarui password user. Hanya dapat diakses oleh user yang sudah terotentikasi.",
)
def updatePassword(data: user.NewPasswordUser, db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    res = db.query(User).where(User.id == user_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ada")

    res.isFirstLogin = data.isFirstLogin
    res.password = bc.hashpw(data.password.encode('utf-8'), bc.gensalt(rounds=12)).decode('utf-8').replace('$2b$', '$2y$')
    db.commit()
    db.refresh(res)

    result = {
        "id": res.id,
        "nip": res.nip,
        "nama": res.name,
        "new_pass": data.password,
        "isFirstLogin": res.isFirstLogin,
    }

    return result

class input_data(BaseModel):
    supabase_url : Union[str,None]
    
@router.put('/update/photo')
async def update_photo_profile(data: input_data, db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    res = db.query(User).where(User.id == user_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ada")
    res.photo_profile = data.supabase_url
    db.commit()
    db.refresh(res)
    return {"message":"Foto berhasil di masukan ke database"}

# @router.get('/user/photo_profile/{image_filename}')
# def get_photo_profile(filename: str):
#     file_path = os.path.join(UPLOAD_DIR, filename)
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(file_path)

# @router.get('/me')
# def me(db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
#     res = db.query(User).where(User.id == user_id).first()
#     if not res:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ada")
#     return res