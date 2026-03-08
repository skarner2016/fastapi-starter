from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_env: str = "development"
    app_name: str = "fastapi-starter"
    app_version: str = "0.1.0"
    app_debug: bool = False
    app_timezone: str = "Asia/Shanghai"
    app_timeout: int = 30

    # Log
    log_level: str = "info"
    log_dir: str = "runtime/logs"
    sql_log: bool = False
    log_backup_day: int = 30

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "fastapi_db"
    mysql_pool_size: int = 10
    mysql_pool_recycle: int = 3600

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 86400  # 24 hours in seconds

    @property
    def mysql_url(self) -> str:
        """Get MySQL connection URL"""
        return f"mysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Create settings instance
settings = Settings()
