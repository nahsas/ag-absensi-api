from pydantic import BaseModel

class BaseUser(BaseModel):
    id: int
    name: str
    nik: str
    nip: str

class LoginUser(BaseModel):
    nip: str
    password: str

class NewPasswordUser(BaseModel):
    password: str
    isFirstLogin: bool
