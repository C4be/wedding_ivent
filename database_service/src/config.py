from pydantic_settings import BaseSettings

class DBConfig(BaseSettings):
    host: str = 'localhost'
    port: int = 5432
    user: str = 'postgres'
    password: str = 'postgres'
    database: str = 'wedding_db'

    @property
    def dsn(self) -> str:
        """Возвращает строку подключения к базе данных в формате, который понимает SQLAlchemy."""
        return f'postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'

    model_config = {
        'env_prefix': 'DB_',
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        "extra": "ignore",
    }

class AppConfig(BaseSettings):
    debug: bool = False

    model_config = {
        'env_prefix': 'APP_',
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        "extra": "ignore",
    }

db_config = DBConfig()
app_config = AppConfig()