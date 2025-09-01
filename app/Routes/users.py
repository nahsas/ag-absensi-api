from datetime import timedelta
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy.orm import Session
import bcrypt as bc

from app.Core.Database import get_db
from app.Core.Essential import create_access_token, get_auth_user
from app.Models.User import User
from app.Schema import user
from pydantic import BaseModel, Field

# Definisikan Pydantic models untuk respons
class LoginResponse(BaseModel):
    id: UUID
    nip: str
    nama: str = Field(alias="name")
    posisi_perusahaan: str
    isFirstLogin: bool
    token: str
    token_type: str

class UpdatePasswordResponse(BaseModel):
    id: UUID
    nip: str
    nama: str = Field(alias="nama")
    isFirstLogin: bool
    new_pass: Optional[str] = Field(..., description="This field is for testing purposes and should not be returned in a production environment.")


router = APIRouter()

@router.post(
    '/auth/login',
    summary="Login user",
    description="Endpoint untuk user login menggunakan NIP dan password. Jika berhasil, akan mengembalikan token otentikasi.",
    response_model=LoginResponse,
)
def get_users(data: user.LoginUser, db: Session = Depends(get_db)):
    res = db.query(User).where(User.nip == data.nip).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nip tidak terdaftar di sistem")

    # Pastikan password yang tersimpan di DB adalah format yang benar
    # FastAPI akan otomatis menangani error 500 jika formatnya salah,
    # tapi pengecekan ini bisa menghindari itu.
    if res.password.startswith('$2a$') or res.password.startswith('$2b$'):
        hashed_password = res.password.encode('utf-8')
    else:
        # Jika password tidak dalam format hash, asumsikan itu password lama dan
        # hash ulang dengan format baru ($2y$)
        # NOTE: Ini hanya contoh, di produksi sebaiknya dipastikan formatnya selalu benar.
        hashed_password = res.password.encode('utf-8').replace(b'$2b$', b'$2y$')
    
    check_password = bc.checkpw(data.password.encode('utf-8'), hashed_password)
    
    if not check_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password salah")

    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(res.id)},
        expires_delta=access_token_expires
    )

    result = {
        "id": res.id,
        "nip": res.nip,
        "name": res.name,
        "posisi_perusahaan": res.position,
        "isFirstLogin": res.isFirstLogin,
        "token": access_token,
        "token_type": "bearer"
    }

    return result

@router.put(
    '/update/password',
    summary="Update password user",
    description="Endpoint untuk memperbarui password user. Hanya dapat diakses oleh user yang sudah terotentikasi.",
    response_model=UpdatePasswordResponse
)
def updatePassword(data: user.NewPasswordUser, db: Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    res = db.query(User).where(User.id == user_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akun tidak ada")

    res.isFirstLogin = data.isFirstLogin
    # Pastikan format hash adalah $2y$ untuk kompatibilitas yang lebih baik
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