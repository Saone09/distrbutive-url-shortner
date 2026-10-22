"""
tests/conftest.py — Shared pytest fixtures
Uses an in-memory SQLite database so tests never touch the development DB.
Rate limiting is disabled in the test config.
"""
import pytest 
from datetime import datetime ,timezone ,timedelta 
from app import create_app 
from app .extensions import db as _db 
from app .models .url import URL 
from app .models .click_event import ClickEvent 
@pytest .fixture (scope ="session")
def app ():
    """
    Create a Flask application configured for testing.
    Session-scoped: one app instance for all tests.
    """
    application =create_app ("testing")
    return application 
@pytest .fixture (scope ="session")
def client (app ):
    """Flask test client — session-scoped."""
    return app .test_client ()
@pytest .fixture (scope ="function",autouse =True )
def clean_db (app ):
    """
    Create all tables before each test and drop them after.
    This guarantees tests are fully isolated.
    """
    with app .app_context ():
        _db .create_all ()
        yield 
        _db .session .remove ()
        _db .drop_all ()
@pytest .fixture 
def db (app ):
    """Expose the db object within an app context for direct model access."""
    with app .app_context ():
        yield _db 
@pytest .fixture 
def sample_url (app ):
    """Insert a known URL into the DB and return its model instance."""
    with app .app_context ():
        url =URL (
        short_code ="testXYZ",
        original_url ="https://example.com/test-page",
        title ="Test URL",
        )
        _db .session .add (url )
        _db .session .commit ()

        return _db .session .get (URL ,url .id )
@pytest .fixture 
def expired_url (app ):
    """Insert an already-expired URL."""
    with app .app_context ():
        url =URL (
        short_code ="expiredABC",
        original_url ="https://example.com/expired",
        expires_at =datetime .now (timezone .utc )-timedelta (hours =1 ),
        )
        _db .session .add (url )
        _db .session .commit ()
        return _db .session .get (URL ,url .id )
@pytest .fixture 
def future_url (app ):
    """Insert a URL that expires in the future (not yet expired)."""
    with app .app_context ():
        url =URL (
        short_code ="futureURL",
        original_url ="https://example.com/future",
        expires_at =datetime .now (timezone .utc )+timedelta (days =30 ),
        )
        _db .session .add (url )
        _db .session .commit ()
        return _db .session .get (URL ,url .id )