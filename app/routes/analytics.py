"""
app/routes/analytics.py — REST API endpoints for analytics
Prefix: /api (set in app factory)
Endpoints:
  GET /api/analytics/overview                    Global dashboard stats
  GET /api/analytics/clicks-over-time            Daily click trend (30 days)
  GET /api/analytics/url-creation-trend          Daily URL creation trend
  GET /api/urls/<short_code>/analytics           Per-URL analytics
"""
from flask import Blueprint ,jsonify ,request 
from app .services .analytics_service import (
get_overview_stats ,
get_clicks_over_time ,
get_url_analytics ,
get_url_creation_trend ,
)
analytics_bp =Blueprint ("analytics",__name__ )
@analytics_bp .route ("/analytics/overview",methods =["GET"])
def overview ():
    """Return global dashboard summary statistics."""
    stats =get_overview_stats ()
    return jsonify (stats ),200 
@analytics_bp .route ("/analytics/clicks-over-time",methods =["GET"])
def clicks_over_time ():
    """
    Return daily click counts.
    Query params:
      days (int, 7–365, default=30)
    """
    try :
        days =int (request .args .get ("days",30 ))
        days =max (7 ,min (365 ,days ))
    except ValueError :
        days =30 
    data =get_clicks_over_time (days =days )
    return jsonify ({"data":data ,"days":days }),200 
@analytics_bp .route ("/analytics/url-creation-trend",methods =["GET"])
def url_creation_trend ():
    """Return daily URL creation counts."""
    try :
        days =int (request .args .get ("days",30 ))
        days =max (7 ,min (365 ,days ))
    except ValueError :
        days =30 
    data =get_url_creation_trend (days =days )
    return jsonify ({"data":data ,"days":days }),200 
@analytics_bp .route ("/urls/<string:short_code>/analytics",methods =["GET"])
def url_analytics (short_code :str ):
    """
    Return detailed analytics for a single short URL.
    Query params:
      days (int, 7–365, default=30)
    """
    try :
        days =int (request .args .get ("days",30 ))
        days =max (7 ,min (365 ,days ))
    except ValueError :
        days =30 
    data =get_url_analytics (short_code =short_code ,days =days )
    if data is None :
        return jsonify ({"error":"Not Found","message":"Short URL not found."}),404 
    return jsonify (data ),200 