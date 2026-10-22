"""
tests/test_urls.py — URL creation, listing, deletion, and validation tests
"""
import pytest 
import json 

class TestCreateURL :
    def test_create_valid_url (self ,client ):
        """POST /api/urls with a valid URL returns 201 and a short_code."""
        res =client .post (
        "/api/urls",
        json ={"url":"https://www.python.org/docs"},
        )
        assert res .status_code ==201 
        data =res .get_json ()
        assert "url"in data 
        assert "short_code"in data ["url"]
        assert "short_url"in data ["url"]
        assert len (data ["url"]["short_code"])==7 
        assert data ["url"]["original_url"]=="https://www.python.org/docs"
    def test_create_url_with_title (self ,client ):
        res =client .post (
        "/api/urls",
        json ={"url":"https://flask.palletsprojects.com/","title":"Flask Docs"},
        )
        assert res .status_code ==201 
        assert res .get_json ()["url"]["title"]=="Flask Docs"
    def test_create_url_with_custom_code (self ,client ):
        res =client .post (
        "/api/urls",
        json ={"url":"https://github.com","custom_code":"my-github"},
        )
        assert res .status_code ==201 
        assert res .get_json ()["url"]["short_code"]=="my-github"
    def test_create_url_with_expiry (self ,client ):
        res =client .post (
        "/api/urls",
        json ={
        "url":"https://example.com/limited",
        "expires_at":"2099-12-31T23:59:59",
        },
        )
        assert res .status_code ==201 
        assert res .get_json ()["url"]["expires_at"]is not None 
    def test_short_codes_are_unique (self ,client ):
        """Creating multiple URLs must produce different short codes."""
        codes =set ()
        for i in range (10 ):
            res =client .post ("/api/urls",json ={"url":f"https://example.com/{i }"})
            assert res .status_code ==201 
            codes .add (res .get_json ()["url"]["short_code"])
        assert len (codes )==10 
    def test_duplicate_custom_code_returns_409 (self ,client ):
        client .post ("/api/urls",json ={"url":"https://a.com","custom_code":"dupe"})
        res =client .post ("/api/urls",json ={"url":"https://b.com","custom_code":"dupe"})
        assert res .status_code ==409 
    def test_no_json_body_returns_400 (self ,client ):
        res =client .post ("/api/urls",data ="not json",content_type ="text/plain")
        assert res .status_code ==400 
    def test_missing_url_field_returns_400 (self ,client ):
        res =client .post ("/api/urls",json ={"title":"No URL"})
        assert res .status_code ==400 

class TestURLValidation :
    """Ensure invalid URLs are rejected before any DB operation."""
    INVALID_URLS =[
    "",
    "   ",
    "ftp://files.example.com",
    "javascript:alert(1)",
    "data:text/html,<h1>hi</h1>",
    "not-a-url",
    "http://",
    "x"*2049 ,
    ]
    @pytest .mark .parametrize ("bad_url",INVALID_URLS )
    def test_invalid_url_rejected (self ,client ,bad_url ):
        res =client .post ("/api/urls",json ={"url":bad_url })
        assert res .status_code ==400 ,f"Expected 400 for URL: {bad_url !r }"
    def test_http_url_accepted (self ,client ):
        res =client .post ("/api/urls",json ={"url":"http://example.com/page"})
        assert res .status_code ==201 
    def test_https_url_accepted (self ,client ):
        res =client .post ("/api/urls",json ={"url":"https://secure.example.com/"})
        assert res .status_code ==201 
    def test_expiry_in_past_rejected (self ,client ):
        res =client .post (
        "/api/urls",
        json ={"url":"https://example.com","expires_at":"2000-01-01T00:00:00"},
        )
        assert res .status_code ==400 
    def test_custom_code_too_short_rejected (self ,client ):
        res =client .post ("/api/urls",json ={"url":"https://a.com","custom_code":"ab"})
        assert res .status_code ==400 
    def test_custom_code_with_spaces_rejected (self ,client ):
        res =client .post ("/api/urls",json ={"url":"https://a.com","custom_code":"my code"})
        assert res .status_code ==400 

class TestListURLs :
    def test_list_returns_200 (self ,client ):
        res =client .get ("/api/urls")
        assert res .status_code ==200 
        data =res .get_json ()
        assert "urls"in data 
        assert "total"in data 
        assert "page"in data 
    def test_list_empty_initially (self ,client ):
        data =client .get ("/api/urls").get_json ()
        assert data ["total"]==0 
        assert data ["urls"]==[]
    def test_list_includes_created_url (self ,client ):
        client .post ("/api/urls",json ={"url":"https://python.org"})
        data =client .get ("/api/urls").get_json ()
        assert data ["total"]==1 
    def test_pagination (self ,client ):
        for i in range (5 ):
            client .post ("/api/urls",json ={"url":f"https://example.com/{i }"})
        data =client .get ("/api/urls?page=1&per_page=2").get_json ()
        assert len (data ["urls"])==2 
        assert data ["total"]==5 
        assert data ["pages"]==3 
    def test_search_filter (self ,client ):
        client .post ("/api/urls",json ={"url":"https://python.org/docs"})
        client .post ("/api/urls",json ={"url":"https://flask.palletsprojects.com"})
        data =client .get ("/api/urls?search=python").get_json ()
        assert data ["total"]==1 

class TestGetURL :
    def test_get_existing_url (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://example.com"}).get_json ()
        code =create ["url"]["short_code"]
        res =client .get (f"/api/urls/{code }")
        assert res .status_code ==200 
        assert res .get_json ()["url"]["short_code"]==code 
    def test_get_nonexistent_url_returns_404 (self ,client ):
        res =client .get ("/api/urls/doesnotexist")
        assert res .status_code ==404 

class TestDeleteURL :
    def test_delete_existing_url (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://example.com"}).get_json ()
        code =create ["url"]["short_code"]
        res =client .delete (f"/api/urls/{code }")
        assert res .status_code ==200 
        assert "deleted"in res .get_json ()["message"].lower ()
    def test_deleted_url_no_longer_redirects (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://example.com"}).get_json ()
        code =create ["url"]["short_code"]
        client .delete (f"/api/urls/{code }")

        res =client .get (f"/{code }")
        assert res .status_code ==404 
    def test_delete_nonexistent_returns_404 (self ,client ):
        res =client .delete ("/api/urls/nocode")
        assert res .status_code ==404 