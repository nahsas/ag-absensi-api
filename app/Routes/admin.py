from array import array
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.Core.Database import get_db
from app.Core.Essential import create_lembur_code, get_auth_user
from app.Models.User import User
from app.Models.UserLembur import Lembur, UserLembur
from typing import List

router = APIRouter()

@router.get('/user_ready_lembur')
def get_user(date_start:datetime, date_end:datetime, db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'superadmin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    # Ambil semua user yang TIDAK terkait dengan lembur pada rentang tanggal tersebut
    # Cari lembur yang overlap dengan rentang tanggal yang diberikan
    overlapping_lembur = db.query(UserLembur.user_id).join(Lembur).filter(
        Lembur.start_date >= date_start,
        Lembur.end_date <= date_end
    ).distinct().all()
    overlapping_user_ids = [row[0] for row in overlapping_lembur]

    users_not_in_lembur = db.query(User).filter(~User.id.in_(overlapping_user_ids)).all()

    return users_not_in_lembur

@router.post('/set_lembur')
def set_lembur(user_id_list: List[str], date_start:datetime, date_end:datetime, db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'superadmin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    lembur_code = create_lembur_code(db)
    new_lembur = Lembur(
        id=str(uuid.uuid4()),
        code=lembur_code,
        start_date=date_start,
        end_date=date_end
    )

    db.add(new_lembur)
    db.commit()
    db.refresh(new_lembur)

    user_name_list = []

    for user_id in user_id_list:
        user = db.query(User).where(User.id == user_id).first().name
        user_name_list.append(user)

        apply_user_has_lembur = UserLembur(
            user_id=user_id,
            lembur_id=new_lembur.id
        )
        db.add(apply_user_has_lembur)
        db.commit()
    
    return {f"Berhasil membuat lembur untuk {user_name_list}"}