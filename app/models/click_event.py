"""
app/models/click_event.py — ClickEvent model
Records every successful redirect event.
Privacy design
--------------
* Raw IP addresses are NOT stored.
* If visitor_hash is needed for deduplication, it is a SHA-256 of
  (IP + date + daily salt) — not reversible to the original IP.
* Referrer and user-agent are stored as-is because they are not personal
  data under most privacy frameworks, but they can be stripped by setting
  STORE_REFERRER=0 / STORE_USER_AGENT=0 env vars.
"""
from datetime import datetime ,timezone 
import hashlib 
from app .extensions import db 
class ClickEvent (db .Model ):
    """
    A single click/redirect event linked to a URL.
    Columns
    -------
    id          : Internal integer primary key.
    url_id      : Foreign key to urls.id.
    clicked_at  : UTC timestamp of the redirect.
    referrer    : HTTP Referer header value (may be empty).
    user_agent  : HTTP User-Agent header value (may be empty).
    visitor_hash: Privacy-safe daily hash for approximate unique-visitor counts.
    """
    __tablename__ ="click_events"
    id =db .Column (db .Integer ,primary_key =True )
    url_id =db .Column (
    db .Integer ,
    db .ForeignKey ("urls.id",ondelete ="CASCADE"),
    nullable =False ,
    index =True ,
    )
    clicked_at =db .Column (
    db .DateTime (timezone =True ),
    nullable =False ,
    default =lambda :datetime .now (timezone .utc ),
    index =True ,
    )
    referrer =db .Column (db .String (2048 ),nullable =True )
    user_agent =db .Column (db .String (512 ),nullable =True )

    visitor_hash =db .Column (db .String (64 ),nullable =True )

    url =db .relationship ("URL",back_populates ="click_events")

    @staticmethod 
    def make_visitor_hash (ip_address :str ,salt :str ="")->str :
        """
        Create a one-way daily hash from an IP address.
        Parameters
        ----------
        ip_address : The raw client IP (never stored).
        salt       : A daily rotating string to prevent rainbow-table attacks.
                     Use today's date string as the salt: str(date.today()).
        """
        raw =f"{ip_address }:{salt }".encode ()
        return hashlib .sha256 (raw ).hexdigest ()

    def to_dict (self )->dict :
        return {
        "id":self .id ,
        "url_id":self .url_id ,
        "clicked_at":self .clicked_at .isoformat ()if self .clicked_at else None ,
        "referrer":self .referrer ,
        "user_agent":self .user_agent ,
        }
    def __repr__ (self )->str :
        return f"<ClickEvent id={self .id } url_id={self .url_id }>"