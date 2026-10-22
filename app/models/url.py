"""
app/models/url.py — URL model
Stores shortened URLs and their metadata.
Indexes are defined on short_code (unique lookup) and created_at (time queries).
"""
from datetime import datetime ,timezone 
from app .extensions import db 
class URL (db .Model ):
    """
    Represents a shortened URL entry.
    Columns
    -------
    id          : Internal integer primary key (not exposed via API).
    short_code  : 7-character URL-safe token; the public identifier.
    original_url: The destination URL.
    title       : Optional human-readable title for display.
    created_at  : UTC timestamp of creation.
    expires_at  : Optional UTC expiry; NULL means no expiry.
    is_active   : Soft-delete flag; False hides the URL without data loss.
    click_count : Denormalized counter updated on each redirect for fast reads.
    """
    __tablename__ ="urls"
    id =db .Column (db .Integer ,primary_key =True )
    short_code =db .Column (db .String (20 ),unique =True ,nullable =False ,index =True )
    original_url =db .Column (db .Text ,nullable =False )
    title =db .Column (db .String (255 ),nullable =True )
    created_at =db .Column (
    db .DateTime (timezone =True ),
    nullable =False ,
    default =lambda :datetime .now (timezone .utc ),
    index =True ,
    )
    expires_at =db .Column (db .DateTime (timezone =True ),nullable =True )
    is_active =db .Column (db .Boolean ,nullable =False ,default =True ,index =True )
    click_count =db .Column (db .Integer ,nullable =False ,default =0 )

    click_events =db .relationship (
    "ClickEvent",back_populates ="url",cascade ="all, delete-orphan",lazy ="dynamic"
    )

    @property 
    def is_expired (self )->bool :
        """Return True if an expiry date is set and has passed."""
        if self .expires_at is None :
            return False 
        now =datetime .now (timezone .utc )

        exp =self .expires_at 
        if exp .tzinfo is None :
            exp =exp .replace (tzinfo =timezone .utc )
        return now >=exp 
    @property 
    def is_accessible (self )->bool :
        """Return True only if the URL is active AND not expired."""
        return self .is_active and not self .is_expired 

    def to_dict (self ,include_original :bool =True )->dict :
        """
        Serialize to a safe API response dict.
        Omits internal ``id``; exposes ``short_code`` as the public identifier.
        """
        from flask import current_app 
        base_url =current_app .config .get ("BASE_URL","http://127.0.0.1:5000")
        data ={
        "short_code":self .short_code ,
        "short_url":f"{base_url }/{self .short_code }",
        "title":self .title ,
        "created_at":self .created_at .isoformat ()if self .created_at else None ,
        "expires_at":self .expires_at .isoformat ()if self .expires_at else None ,
        "is_active":self .is_active ,
        "is_expired":self .is_expired ,
        "click_count":self .click_count ,
        }
        if include_original :
            data ["original_url"]=self .original_url 
        return data 
    def __repr__ (self )->str :
        return f"<URL short_code={self .short_code !r } active={self .is_active }>"