from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_DATABASE: str
    DB_USERNAME: str
    DB_PASSWORD: str
    OFFICE_LAT : float
    OFFICE_LON : float

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
setting = Settings()