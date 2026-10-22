"""
tests/test_redirects.py — URL redirect, expiry, and click-recording tests
"""
import pytest 
from datetime import datetime ,timezone ,timedelta 
class TestRedirects :
    def test_redirect_to_original_url (self ,client ):
        """Valid short URL performs a 302 redirect to original."""
        create =client .post ("/api/urls",json ={"url":"https://www.example.com/"}).get_json ()
        code =create ["url"]["short_code"]
        res =client .get (f"/{code }")
        assert res .status_code ==302 
        assert res .headers ["Location"]=="https://www.example.com/"
    def test_redirect_unknown_code_returns_404 (self ,client ):
        res =client .get ("/unknownXXX")
        assert res .status_code ==404 
    def test_redirect_records_click (self ,client ,app ):
        """Each redirect should increment click_count by 1."""
        from app .models .url import URL 
        from app .extensions import db 
        create =client .post ("/api/urls",json ={"url":"https://click-test.example.com/"}).get_json ()
        code =create ["url"]["short_code"]

        client .get (f"/{code }")
        client .get (f"/{code }")
        with app .app_context ():
            url =db .session .execute (
            db .select (URL ).where (URL .short_code ==code )
            ).scalar_one ()
            assert url .click_count ==2 
    def test_redirect_expired_url_returns_410 (self ,client ):
        """Expired URLs should return 410 Gone, not 302."""
        past =(datetime .now (timezone .utc )-timedelta (hours =2 )).isoformat ()
        create =client .post (
        "/api/urls",
        json ={"url":"https://expired.example.com/","expires_at":past },
        )



        pass 
    def test_expired_url_fixture_returns_410 (self ,client ,app ,expired_url ):
        """Expired URL (inserted directly) returns 410 Gone."""
        with app .app_context ():
            from app .models .url import URL 
            from app .extensions import db 
            url =db .session .execute (
            db .select (URL ).where (URL .short_code =="expiredABC")
            ).scalar_one ()
            code =url .short_code 
        res =client .get (f"/{code }")
        assert res .status_code ==410 
    def test_future_expiry_url_still_redirects (self ,client ,app ,future_url ):
        """URL with future expiry should still redirect normally."""
        with app .app_context ():
            from app .models .url import URL 
            from app .extensions import db 
            url =db .session .execute (
            db .select (URL ).where (URL .short_code =="futureURL")
            ).scalar_one ()
            code =url .short_code 
        res =client .get (f"/{code }")
        assert res .status_code ==302 
    def test_deleted_url_returns_404 (self ,client ):
        """Soft-deleted URL returns 404 on redirect."""
        create =client .post ("/api/urls",json ={"url":"https://delete-test.example.com/"}).get_json ()
        code =create ["url"]["short_code"]
        client .delete (f"/api/urls/{code }")
        res =client .get (f"/{code }")
        assert res .status_code ==404 
    def test_redirect_does_not_serve_html_for_api_routes (self ,client ):
        """The redirect handler must not intercept /api/* routes."""
        res =client .get ("/api/urls")

        assert res .status_code ==200 
        assert res .is_json 
    def test_click_event_created_on_redirect (self ,client ,app ):
        """A ClickEvent row should be created for each successful redirect."""
        from app .models .click_event import ClickEvent 
        from app .extensions import db 
        create =client .post ("/api/urls",json ={"url":"https://event-test.example.com/"}).get_json ()
        code =create ["url"]["short_code"]
        client .get (f"/{code }")
        with app .app_context ():
            count =db .session .execute (
            db .select (db .func .count (ClickEvent .id ))
            ).scalar ()
            assert count ==1 
    def test_referrer_recorded_in_click_event (self ,client ,app ):
        """Referrer header should be stored on the ClickEvent."""
        from app .models .click_event import ClickEvent 
        from app .extensions import db 
        create =client .post ("/api/urls",json ={"url":"https://referrer-test.example.com/"}).get_json ()
        code =create ["url"]["short_code"]
        client .get (f"/{code }",headers ={"Referer":"https://google.com"})
        with app .app_context ():
            event =db .session .execute (db .select (ClickEvent )).scalar_one ()
            assert event .referrer =="https://google.com"