"""
app/services/url_service.py — Business logic for URL operations
Keeps routes thin and logic testable in isolation.
"""
import secrets 
import string 
from datetime import datetime ,timezone 
from typing import Optional 
from urllib .parse import urlparse 
from sqlalchemy .exc import IntegrityError 
from app .extensions import db 
from app .models .url import URL 
from app .models .click_event import ClickEvent 

ALLOWED_SCHEMES ={"http","https"}
def validate_url (url :str )->tuple [bool ,str ]:
    """
    Validate that a URL is safe to store and redirect to.
    Returns (True, "") on success.
    Returns (False, reason) on failure.
    Checks performed:
    - Not empty / not just whitespace
    - Parseable by urllib
    - Scheme is http or https only (blocks javascript:, ftp:, data:, etc.)
    - Has a non-empty hostname
    - Maximum length guard
    """
    if not url or not url .strip ():
        return False ,"URL must not be empty."
    url =url .strip ()
    if len (url )>2048 :
        return False ,"URL exceeds the maximum allowed length of 2048 characters."
    try :
        parsed =urlparse (url )
    except Exception :
        return False ,"URL could not be parsed."
    if parsed .scheme .lower ()not in ALLOWED_SCHEMES :
        return False ,f"URL scheme '{parsed .scheme }' is not allowed. Use http or https."
    if not parsed .netloc :
        return False ,"URL must include a valid hostname."


    return True ,""

_ALPHABET =string .ascii_letters +string .digits 
def generate_short_code (length :int =7 )->str :
    """
    Generate a cryptographically random, URL-safe short code.
    Uses ``secrets`` module (CSPRNG) so codes are unpredictable.
    Length-7 gives 62^7 ≈ 3.5 trillion unique codes.
    """
    return "".join (secrets .choice (_ALPHABET )for _ in range (length ))
def _unique_short_code (length :int ,max_retries :int =10 )->str :
    """
    Generate a short code that doesn't already exist in the database.
    Raises RuntimeError if all retries are exhausted (extremely unlikely).
    """
    for attempt in range (max_retries ):
        code =generate_short_code (length )
        exists =db .session .execute (
        db .select (URL .id ).where (URL .short_code ==code )
        ).scalar_one_or_none ()
        if not exists :
            return code 
    raise RuntimeError (
    f"Could not generate a unique short code after {max_retries } attempts. "
    "Consider increasing SHORT_CODE_LENGTH."
    )

def create_short_url (
original_url :str ,
title :Optional [str ]=None ,
expires_at :Optional [datetime ]=None ,
custom_code :Optional [str ]=None ,
)->tuple [URL ,str |None ]:
    """
    Create a new shortened URL.
    Parameters
    ----------
    original_url : The destination URL (will be validated).
    title        : Optional display title.
    expires_at   : Optional UTC expiry datetime.
    custom_code  : Optional user-supplied short code.
    Returns
    -------
    (url_object, error_message)
    url_object is None when error_message is set.
    """
    from flask import current_app 

    valid ,reason =validate_url (original_url )
    if not valid :
        return None ,reason 

    if custom_code :
        custom_code =custom_code .strip ()
        if not (3 <=len (custom_code )<=20 ):
            return None ,"Custom code must be 3–20 characters."
        allowed =set (string .ascii_letters +string .digits +"-_")
        if not all (c in allowed for c in custom_code ):
            return None ,"Custom code may only contain letters, digits, hyphens, and underscores."

        existing =db .session .execute (
        db .select (URL ).where (URL .short_code ==custom_code )
        ).scalar_one_or_none ()
        if existing :
            return None ,f"Short code '{custom_code }' is already taken."
        short_code =custom_code 
    else :
        length =current_app .config .get ("SHORT_CODE_LENGTH",7 )
        max_retries =current_app .config .get ("MAX_COLLISION_RETRIES",10 )
        try :
            short_code =_unique_short_code (length ,max_retries )
        except RuntimeError as e :
            return None ,str (e )
    url =URL (
    short_code =short_code ,
    original_url =original_url .strip (),
    title =title .strip ()if title else None ,
    expires_at =expires_at ,
    )
    try :
        db .session .add (url )
        db .session .commit ()
    except IntegrityError :
        db .session .rollback ()
        return None ,"A URL with that short code already exists (race condition). Please retry."
    return url ,None 
def get_url_by_code (short_code :str )->Optional [URL ]:
    """Fetch a URL by short code regardless of active/expired status."""
    return db .session .execute (
    db .select (URL ).where (URL .short_code ==short_code )
    ).scalar_one_or_none ()
def get_active_url_by_code (short_code :str )->tuple [Optional [URL ],str |None ]:
    """
    Fetch an active, non-expired URL by short code.
    Returns (url, None) on success.
    Returns (None, reason) when the URL cannot be used.
    """
    url =get_url_by_code (short_code )
    if url is None :
        return None ,"Short URL not found."
    if not url .is_active :
        return None ,"This short URL has been deactivated."
    if url .is_expired :
        return None ,"This short URL has expired."
    return url ,None 
def list_urls (page :int =1 ,per_page :int =20 ,search :str ="")->dict :
    """
    Return a paginated list of active URLs.
    Parameters
    ----------
    page     : 1-based page number.
    per_page : Results per page (max capped at 100).
    search   : Optional filter on original_url or short_code.
    """
    per_page =min (per_page ,100 )
    query =db .select (URL ).where (URL .is_active ==True )
    if search :
        like =f"%{search }%"
        query =query .where (
        db .or_ (URL .original_url .ilike (like ),URL .short_code .ilike (like ))
        )
    query =query .order_by (URL .created_at .desc ())

    total =db .session .execute (
    db .select (db .func .count ()).select_from (query .subquery ())
    ).scalar ()
    offset =(page -1 )*per_page 
    rows =db .session .execute (query .limit (per_page ).offset (offset )).scalars ().all ()
    return {
    "urls":[u .to_dict ()for u in rows ],
    "page":page ,
    "per_page":per_page ,
    "total":total ,
    "pages":(total +per_page -1 )//per_page if total else 0 ,
    }
def delete_url (short_code :str )->tuple [bool ,str ]:
    """
    Soft-delete a URL by setting is_active = False.
    Returns (True, "") on success.
    Returns (False, reason) if not found.
    """
    url =get_url_by_code (short_code )
    if url is None :
        return False ,"URL not found."
    url .is_active =False 
    db .session .commit ()
    return True ,""

def record_click (url :URL ,request )->ClickEvent :
    """
    Record a click event and increment the URL's click counter atomically.
    ``request`` is the Flask request object (passed in rather than imported
    here to keep the service layer testable without a request context).
    """
    from datetime import date 
    referrer =(request .referrer or "")[:2048 ]
    user_agent =(request .headers .get ("User-Agent","")or "")[:512 ]
    ip =request .remote_addr or ""
    salt =str (date .today ())
    visitor_hash =ClickEvent .make_visitor_hash (ip ,salt )if ip else None 
    event =ClickEvent (
    url_id =url .id ,
    referrer =referrer ,
    user_agent =user_agent ,
    visitor_hash =visitor_hash ,
    )
    db .session .add (event )

    db .session .execute (
    db .update (URL ).where (URL .id ==url .id ).values (click_count =URL .click_count +1 )
    )
    db .session .commit ()
    return event 