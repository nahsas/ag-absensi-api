from array import array
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.Core.Database import get_db
from app.Core.Essential import get_auth_user
from app.Models.User import User
from app.Models.UserLembur import Lembur, UserLembur
from typing import List

router = APIRouter()

@router.get('/user_ready_lembur')
def get_user(date_start:datetime, date_end:datetime,db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'admin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    # Ambil semua user yang TIDAK terkait dengan lembur pada rentang tanggal tersebut
    # Cari lembur yang overlap dengan rentang tanggal yang diberikan
    overlapping_lembur = db.query(UserLembur.user_id).join(Lembur).filter(
        Lembur.start_date <= date_end,
        Lembur.end_date >= date_start
    ).distinct().all()
    overlapping_user_ids = [row[0] for row in overlapping_lembur]

    users_not_in_lembur = db.query(User).filter(~User.id.in_(overlapping_user_ids)).all()

    return users_not_in_lembur

@router.post('/set_lembur')
def set_lembur(user_id_list: List[str]):
    # Example: process each user_id in the list
    processed_ids = []
    for user_id in user_id_list:
        processed_ids.append(user_id)
    return {"processed_user_ids": processed_ids}