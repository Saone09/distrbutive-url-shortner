"""
app/services/analytics_service.py — Analytics aggregation queries
All queries return plain dicts/lists — no Flask request context needed,
making them directly testable with pytest.
"""
from datetime import datetime ,timezone ,timedelta 
from typing import Any 
from sqlalchemy import func 
from app .extensions import db 
from app .models .url import URL 
from app .models .click_event import ClickEvent 
def get_overview_stats ()->dict [str ,Any ]:
    """
    Return dashboard summary statistics.
    Computes:
    - total_urls      : Count of active (non-deleted) URLs.
    - total_clicks    : Sum of click_count across all URLs.
    - clicks_today    : Click events with clicked_at >= UTC midnight today.
    - active_urls     : URLs that are active and not expired.
    - most_popular    : Top-5 URLs by click_count.
    - recent_clicks   : Last 10 click events (newest first).
    """

    total_urls =db .session .execute (
    db .select (func .count (URL .id )).where (URL .is_active ==True )
    ).scalar ()or 0 

    total_clicks =db .session .execute (
    db .select (func .sum (URL .click_count )).where (URL .is_active ==True )
    ).scalar ()or 0 

    today_start =datetime .now (timezone .utc ).replace (hour =0 ,minute =0 ,second =0 ,microsecond =0 )
    clicks_today =db .session .execute (
    db .select (func .count (ClickEvent .id )).where (ClickEvent .clicked_at >=today_start )
    ).scalar ()or 0 

    now =datetime .now (timezone .utc )
    active_urls =db .session .execute (
    db .select (func .count (URL .id )).where (
    URL .is_active ==True ,
    db .or_ (URL .expires_at ==None ,URL .expires_at >now ),
    )
    ).scalar ()or 0 

    top_urls_rows =db .session .execute (
    db .select (URL )
    .where (URL .is_active ==True )
    .order_by (URL .click_count .desc ())
    .limit (5 )
    ).scalars ().all ()
    most_popular =[u .to_dict ()for u in top_urls_rows ]

    recent_rows =db .session .execute (
    db .select (ClickEvent )
    .order_by (ClickEvent .clicked_at .desc ())
    .limit (10 )
    ).scalars ().all ()
    recent_clicks =[e .to_dict ()for e in recent_rows ]
    return {
    "total_urls":total_urls ,
    "total_clicks":int (total_clicks ),
    "clicks_today":clicks_today ,
    "active_urls":active_urls ,
    "most_popular":most_popular ,
    "recent_clicks":recent_clicks ,
    }
def get_clicks_over_time (days :int =30 )->list [dict [str ,Any ]]:
    """
    Return daily click counts for the past ``days`` days.
    Returns a list of {"date": "YYYY-MM-DD", "clicks": N} dicts,
    one per day, with zeros for days that had no clicks.
    """
    since =datetime .now (timezone .utc )-timedelta (days =days )
    day_expression =func .date (ClickEvent .clicked_at )
    rows =db .session .execute (
    db .select (
    day_expression .label ("day"),
    func .count (ClickEvent .id ).label ("clicks"),
    )
    .where (ClickEvent .clicked_at >=since )
    .group_by (day_expression )
    .order_by (day_expression )
    ).all ()

    data_map ={str (row .day ):row .clicks for row in rows }

    result =[]
    for i in range (days ):
        day =(datetime .now (timezone .utc )-timedelta (days =days -1 -i )).date ()
        day_str =str (day )
        result .append ({"date":day_str ,"clicks":data_map .get (day_str ,0 )})
    return result 
def get_url_analytics (short_code :str ,days :int =30 )->dict [str ,Any ]|None :
    """
    Return detailed analytics for a single URL.
    Returns None when the short_code is not found.
    """
    url =db .session .execute (
    db .select (URL ).where (URL .short_code ==short_code )
    ).scalar_one_or_none ()
    if url is None :
        return None 
    since =datetime .now (timezone .utc )-timedelta (days =days )

    day_expression =func .date (ClickEvent .clicked_at )
    rows =db .session .execute (
    db .select (
    day_expression .label ("day"),
    func .count (ClickEvent .id ).label ("clicks"),
    )
    .where (ClickEvent .url_id ==url .id ,ClickEvent .clicked_at >=since )
    .group_by (day_expression )
    .order_by (day_expression )
    ).all ()
    data_map ={str (row .day ):row .clicks for row in rows }
    daily_clicks =[]
    for i in range (days ):
        day =(datetime .now (timezone .utc )-timedelta (days =days -1 -i )).date ()
        day_str =str (day )
        daily_clicks .append ({"date":day_str ,"clicks":data_map .get (day_str ,0 )})

    referrer_rows =db .session .execute (
    db .select (
    ClickEvent .referrer ,
    func .count (ClickEvent .id ).label ("count"),
    )
    .where (ClickEvent .url_id ==url .id ,ClickEvent .referrer !=None ,ClickEvent .referrer !="")
    .group_by (ClickEvent .referrer )
    .order_by (func .count (ClickEvent .id ).desc ())
    .limit (10 )
    ).all ()
    top_referrers =[{"referrer":r .referrer ,"count":r .count }for r in referrer_rows ]

    clicks_in_window =db .session .execute (
    db .select (func .count (ClickEvent .id )).where (
    ClickEvent .url_id ==url .id ,
    ClickEvent .clicked_at >=since ,
    )
    ).scalar ()or 0 
    return {
    "url":url .to_dict (),
    "daily_clicks":daily_clicks ,
    "top_referrers":top_referrers ,
    "clicks_in_window":clicks_in_window ,
    "window_days":days ,
    }
def get_url_creation_trend (days :int =30 )->list [dict [str ,Any ]]:
    """
    Return the number of URLs created per day over the past ``days`` days.
    Useful for a "URL creation trend" chart on the dashboard.
    """
    since =datetime .now (timezone .utc )-timedelta (days =days )
    day_expression =func .date (URL .created_at )
    rows =db .session .execute (
    db .select (
    day_expression .label ("day"),
    func .count (URL .id ).label ("count"),
    )
    .where (URL .created_at >=since ,URL .is_active ==True )
    .group_by (day_expression )
    .order_by (day_expression )
    ).all ()
    data_map ={str (row .day ):row .count for row in rows }
    result =[]
    for i in range (days ):
        day =(datetime .now (timezone .utc )-timedelta (days =days -1 -i )).date ()
        day_str =str (day )
        result .append ({"date":day_str ,"count":data_map .get (day_str ,0 )})
    return result 