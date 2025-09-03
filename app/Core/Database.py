from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.Core.Env import setting

engine = create_engine(f'mysql+mysqlconnector://{setting.DB_USERNAME}:{setting.DB_PASSWORD}@{setting.DB_HOST}:{setting.DB_PORT}/{setting.DB_DATABASE}',
 pool_pre_ping=True,   #  cek koneksi sebelum dipakai
    pool_recycle=3600,    #  recycle tiap 1 jam
#antisipasi koneksi sebelum di pakek 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.close()
        raise
    finally:
        db.close()