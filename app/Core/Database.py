from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.Core.Env import setting

engine = create_engine(f'postgresql://{setting.DB_USERNAME}:{setting.DB_PASSWORD}@{setting.DB_HOST}:{setting.DB_PORT}/{setting.DB_DATABASE}')

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