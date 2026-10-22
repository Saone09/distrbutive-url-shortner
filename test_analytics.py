"""
tests/test_analytics.py — Analytics endpoint and aggregation tests
"""
import pytest 
class TestOverviewAnalytics :
    def test_overview_returns_200 (self ,client ):
        res =client .get ("/api/analytics/overview")
        assert res .status_code ==200 
    def test_overview_structure (self ,client ):
        data =client .get ("/api/analytics/overview").get_json ()
        assert "total_urls"in data 
        assert "total_clicks"in data 
        assert "clicks_today"in data 
        assert "active_urls"in data 
        assert "most_popular"in data 
        assert "recent_clicks"in data 
    def test_overview_counts_zero_initially (self ,client ):
        data =client .get ("/api/analytics/overview").get_json ()
        assert data ["total_urls"]==0 
        assert data ["total_clicks"]==0 
        assert data ["clicks_today"]==0 
    def test_overview_counts_after_creation (self ,client ):
        client .post ("/api/urls",json ={"url":"https://counter-test.com"})
        data =client .get ("/api/analytics/overview").get_json ()
        assert data ["total_urls"]==1 
    def test_click_increments_total (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://click-counter.com"}).get_json ()
        code =create ["url"]["short_code"]
        client .get (f"/{code }")
        client .get (f"/{code }")
        data =client .get ("/api/analytics/overview").get_json ()
        assert data ["total_clicks"]==2 
    def test_most_popular_sorted_by_clicks (self ,client ):
        """The top URL should be the one with the most clicks."""
        r1 =client .post ("/api/urls",json ={"url":"https://popular.com"}).get_json ()
        r2 =client .post ("/api/urls",json ={"url":"https://unpopular.com"}).get_json ()
        popular_code =r1 ["url"]["short_code"]
        unpopular_code =r2 ["url"]["short_code"]

        for _ in range (3 ):
            client .get (f"/{popular_code }")
        client .get (f"/{unpopular_code }")
        data =client .get ("/api/analytics/overview").get_json ()
        top =data ["most_popular"]
        assert len (top )>=1 
        assert top [0 ]["short_code"]==popular_code 
class TestClicksOverTime :
    def test_clicks_over_time_returns_200 (self ,client ):
        res =client .get ("/api/analytics/clicks-over-time")
        assert res .status_code ==200 
    def test_clicks_over_time_structure (self ,client ):
        data =client .get ("/api/analytics/clicks-over-time?days=7").get_json ()
        assert "data"in data 
        assert len (data ["data"])==7 
        for item in data ["data"]:
            assert "date"in item 
            assert "clicks"in item 
    def test_clicks_over_time_default_30_days (self ,client ):
        data =client .get ("/api/analytics/clicks-over-time").get_json ()
        assert len (data ["data"])==30 
    def test_url_creation_trend_returns_200 (self ,client ):
        res =client .get ("/api/analytics/url-creation-trend")
        assert res .status_code ==200 
    def test_url_creation_trend_structure (self ,client ):
        data =client .get ("/api/analytics/url-creation-trend").get_json ()
        assert "data"in data 
        assert len (data ["data"])==30 
class TestPerURLAnalytics :
    def test_per_url_analytics_returns_200 (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://perurl.example.com"}).get_json ()
        code =create ["url"]["short_code"]
        res =client .get (f"/api/urls/{code }/analytics")
        assert res .status_code ==200 
    def test_per_url_analytics_structure (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://struct.example.com"}).get_json ()
        code =create ["url"]["short_code"]
        data =client .get (f"/api/urls/{code }/analytics").get_json ()
        assert "url"in data 
        assert "daily_clicks"in data 
        assert "top_referrers"in data 
        assert "clicks_in_window"in data 
    def test_per_url_click_count_matches (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://match.example.com"}).get_json ()
        code =create ["url"]["short_code"]
        client .get (f"/{code }")
        client .get (f"/{code }")
        client .get (f"/{code }")
        data =client .get (f"/api/urls/{code }/analytics").get_json ()
        assert data ["url"]["click_count"]==3 
    def test_per_url_analytics_404_for_unknown (self ,client ):
        res =client .get ("/api/urls/doesnotexist999/analytics")
        assert res .status_code ==404 
    def test_top_referrers_captured (self ,client ):
        create =client .post ("/api/urls",json ={"url":"https://ref.example.com"}).get_json ()
        code =create ["url"]["short_code"]
        client .get (f"/{code }",headers ={"Referer":"https://google.com"})
        client .get (f"/{code }",headers ={"Referer":"https://twitter.com"})
        client .get (f"/{code }",headers ={"Referer":"https://google.com"})
        data =client .get (f"/api/urls/{code }/analytics").get_json ()
        referrers ={r ["referrer"]:r ["count"]for r in data ["top_referrers"]}
        assert referrers .get ("https://google.com")==2 
        assert referrers .get ("https://twitter.com")==1 