"""
app/extensions.py — Shared Flask extension instances
Import from here instead of re-creating extensions in multiple modules.
This avoids circular imports and ensures each extension is initialized once.
"""
from flask_sqlalchemy import SQLAlchemy 
from flask_limiter import Limiter 
from flask_limiter .util import get_remote_address 

db =SQLAlchemy ()

limiter =Limiter (
key_func =get_remote_address ,
default_limits =["200 per day","50 per hour"],
storage_uri ="memory://",
)

try :
    from flask_migrate import Migrate 
    migrate =Migrate ()
except ImportError :
    class _MigrateStub :
        """Stub so app/__init__.py import never fails."""
        def init_app (self ,*args ,**kwargs ):
            pass 
    migrate =_MigrateStub ()