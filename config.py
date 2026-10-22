"""
config.py — Application configuration
Reads settings from environment variables with safe defaults.
Never hardcode secrets here; use .env for local development.
"""
import os 
from dotenv import load_dotenv 

load_dotenv ()
class Config :
    """Base configuration shared across all environments."""

    SECRET_KEY =os .environ .get ("SECRET_KEY","dev-secret-key-change-in-production")

    SQLALCHEMY_TRACK_MODIFICATIONS =False 
    SQLALCHEMY_DATABASE_URI =os .environ .get (
    "DATABASE_URL","sqlite:///url_shortener.db"
    )

    SHORT_CODE_LENGTH =int (os .environ .get ("SHORT_CODE_LENGTH",7 ))
    MAX_COLLISION_RETRIES =10 

    BASE_URL =os .environ .get ("BASE_URL","http://127.0.0.1:5000")

    RATELIMIT_DEFAULT ="200 per day;50 per hour"
    RATELIMIT_STORAGE_URI =os .environ .get ("REDIS_URL","memory://")

    CACHE_TYPE ="RedisCache"if os .environ .get ("REDIS_URL")else "SimpleCache"
    CACHE_REDIS_URL =os .environ .get ("REDIS_URL","")
    CACHE_DEFAULT_TIMEOUT =300 

    URLS_PER_PAGE =int (os .environ .get ("URLS_PER_PAGE",20 ))

    DEBUG =os .environ .get ("FLASK_DEBUG","0")=="1"
class DevelopmentConfig (Config ):
    """Local development — SQLite, debug on."""
    DEBUG =True 
    SQLALCHEMY_DATABASE_URI =os .environ .get (
    "DATABASE_URL","sqlite:///url_shortener_dev.db"
    )
class TestingConfig (Config ):
    """Automated tests — in-memory SQLite, no rate-limit storage."""
    TESTING =True 
    SQLALCHEMY_DATABASE_URI ="sqlite:///:memory:"
    RATELIMIT_ENABLED =False 
    WTF_CSRF_ENABLED =False 
    SECRET_KEY ="test-secret-key"
    BASE_URL ="http://localhost"
class ProductionConfig (Config ):
    """Production — requires real DATABASE_URL and SECRET_KEY env vars."""
    DEBUG =False 
    TESTING =False 
    @classmethod 
    def validate (cls ):
        """Call this at startup to catch missing production settings."""
        if cls .SECRET_KEY =="dev-secret-key-change-in-production":
            raise ValueError ("SECRET_KEY must be set in production environment")
        if "sqlite"in cls .SQLALCHEMY_DATABASE_URI :
            raise ValueError ("PostgreSQL (DATABASE_URL) must be set in production")

config_map ={
"development":DevelopmentConfig ,
"testing":TestingConfig ,
"production":ProductionConfig ,
"default":DevelopmentConfig ,
}
