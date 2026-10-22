"""
app/routes/redirect.py — Short-URL redirect handler
GET /<short_code>
This is intentionally a separate Blueprint so it can be mounted at the root
without conflicting with the /api/* or page routes.
Flow:
  1. Look up short_code in DB
  2. Verify URL is active and not expired
  3. Record click event (referrer, user-agent, privacy-safe visitor hash)
  4. HTTP 302 redirect to original URL
"""
from flask import Blueprint ,redirect ,abort ,request ,render_template ,current_app 
from app .services .url_service import get_active_url_by_code ,record_click 
redirect_bp =Blueprint ("redirect",__name__ )

_CODE_RE =r"[A-Za-z0-9_\-]{3,20}"
@redirect_bp .route (f"/<regex('{_CODE_RE }'):short_code>",methods =["GET"])
def handle_redirect (short_code :str ):
    """Validate, record, and redirect."""
    url ,error =get_active_url_by_code (short_code )
    if error =="Short URL not found.":
        abort (404 ,description ="This short URL does not exist.")
    elif error =="This short URL has expired.":
        return render_template ("expired.html",short_code =short_code ),410 
    elif error :
        abort (404 ,description =error )

    try :
        record_click (url ,request )
    except Exception as exc :
        current_app .logger .error (f"Failed to record click for {short_code }: {exc }")
    return redirect (url .original_url ,code =302 )

from werkzeug .routing import BaseConverter 
class RegexConverter (BaseConverter ):
    def __init__ (self ,url_map ,*items ):
        super ().__init__ (url_map )
        self .regex =items [0 ]