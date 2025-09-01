from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.Routes import absens, izins, sakits, users, cores

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(prefix='/user',router=users.router, tags=["User"])
app.include_router(prefix='/absen',router=absens.router, tags=["Absen"])
app.include_router(prefix='/izin',router=izins.router, tags=["Izin"])
app.include_router(prefix='/sakit',router=sakits.router, tags=["sakit"])
app.include_router(prefix='/core', router=cores.router, tags=["Core"])
