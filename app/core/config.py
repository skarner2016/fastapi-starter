from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_env: str = "development"
    app_name: str = "fastapi-starter"
    app_version: str = "0.1.0"
    app_debug: bool = False

    # Log
    log_level: str = "info"
    log_dir: str = "runtime/logs"

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "fastapi_db"
    mysql_pool_size: int = 10
    mysql_pool_recycle: int = 3600

    @property
    def mysql_url(self) -> str:
        """Get MySQL connection URL"""
        return f"mysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"


# Create settings instance
settings = Settings()
