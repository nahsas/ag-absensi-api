from array import array
from datetime import date, datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.Core.Database import get_db
from app.Core.Essential import create_lembur_code, get_auth_user
from app.Models.User import DinasLuar, HasDinasLuar, User
from app.Models.UserLembur import Lembur, UserLembur
from typing import List

class CreateDinasLuar(BaseModel):
    judul: str
    deskripsi: str
    tanggal_mulai: date
    tanggal_selesai: date

router = APIRouter()

@router.get('/user_ready_lembur')
def get_user(date_start:datetime, date_end:datetime, db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'superadmin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    lembur_selected = db.query(Lembur.id).filter(or_(
        Lembur.start_date.between(date_start, date_end),
        Lembur.end_date.between(date_start, date_end),
        (Lembur.start_date <= date_start) & (Lembur.end_date >= date_end)
    )).distinct().all()
    lembur_selected = [x[0] for x in lembur_selected]
    user_has_lembur = db.query(UserLembur.user_id).where(UserLembur.lembur_id.in_(lembur_selected)).distinct().all()
    users_id = [x[0] for x in user_has_lembur]
    res = db.query(User).where(~User.id.in_(users_id)).all()

    return res

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


@router.get('/user_ready_dinas_luar')
def get_user(date_start:datetime, date_end:datetime, db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'superadmin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    dinas_luar_selected = db.query(DinasLuar.id).filter(or_(
        DinasLuar.tanggal_mulai.between(date_start, date_end),
        DinasLuar.tanggal_selesai.between(date_start, date_end),
        (DinasLuar.tanggal_mulai <= date_start) & (DinasLuar.tanggal_selesai >= date_end)
    )).distinct().all()
    dinas_luar_selected = [x[0] for x in dinas_luar_selected]
    user_has_dinas_luar = db.query(HasDinasLuar.user_id).where(HasDinasLuar.dinas_luar_id.in_(dinas_luar_selected)).distinct().all()
    users_id = [x[0] for x in user_has_dinas_luar]
    res = db.query(User).where(~User.id.in_(users_id)).all()

    return res

@router.post('/set_dinas_luar')
def set_lembur(data:CreateDinasLuar,user_id_list: List[str], db:Session = Depends(get_db), user_id: str = Depends(get_auth_user)):
    user = db.query(User).where(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.role.name != 'superadmin':
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Tidak punya izin untuk akses endpoint ini') 

    new_dinas_luar = DinasLuar(
        id=str(uuid.uuid4()),
        judul = data.judul,
        deskripsi = data.deskripsi,
        tanggal_mulai = data.tanggal_mulai,
        tanggal_selesai = data.tanggal_selesai,
        approved = True
    )

    db.add(new_dinas_luar)
    db.commit()
    db.refresh(new_dinas_luar)

    user_name_list = []

    for user_id in user_id_list:
        user = db.query(User).where(User.id == user_id).first().name
        user_name_list.append(user)

        apply_user_has_dinas_luar = HasDinasLuar(
            user_id=user_id,
            dinas_luar_id=new_dinas_luar.id
        )
        db.add(apply_user_has_dinas_luar)
        db.commit()
    
    return {f"Berhasil membuat dinas luar untuk {user_name_list}"}