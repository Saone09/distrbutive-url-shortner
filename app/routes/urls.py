"""
app/routes/urls.py — REST API endpoints for URL management
Prefix: /api (set in app factory)
Endpoints:
  POST   /api/urls                         Create a new short URL
  GET    /api/urls                         List URLs (paginated)
  GET    /api/urls/<short_code>            Get single URL details
  DELETE /api/urls/<short_code>            Soft-delete a URL
"""
from datetime import datetime ,timezone 
from flask import Blueprint ,jsonify ,request ,current_app ,abort 
from app .extensions import limiter 
from app .services .url_service import (
create_short_url ,
get_url_by_code ,
list_urls ,
delete_url ,
)
urls_bp =Blueprint ("urls",__name__ )

@urls_bp .route ("/urls",methods =["POST"])
@limiter .limit ("30 per minute; 200 per hour")
def create_url ():
    """
    Create a new shortened URL.
    Request JSON body:
    {
        "url": "https://example.com/...",   (required)
        "title": "My Link",                  (optional)
        "expires_at": "2025-12-31T23:59:59", (optional ISO-8601 UTC)
        "custom_code": "my-slug"             (optional)
    }
    Responses:
      201  Created  — {"url": {...}}
      400  Bad Request — {"error": ..., "message": ...}
    """
    data =request .get_json (silent =True )
    if not data :
        return jsonify ({"error":"Bad Request","message":"JSON body required."}),400 
    original_url =data .get ("url","").strip ()
    title =data .get ("title","").strip ()or None 
    custom_code =data .get ("custom_code","").strip ()or None 

    expires_at =None 
    if "expires_at"in data and data ["expires_at"]:
        try :
            raw =data ["expires_at"]

            expires_at =datetime .fromisoformat (raw .replace ("Z","+00:00"))
            if expires_at .tzinfo is None :
                expires_at =expires_at .replace (tzinfo =timezone .utc )
            if expires_at <=datetime .now (timezone .utc ):
                return jsonify ({"error":"Bad Request","message":"Expiry date must be in the future."}),400 
        except ValueError :
            return jsonify ({"error":"Bad Request","message":"Invalid expires_at format. Use ISO-8601."}),400 
    url_obj ,error =create_short_url (
    original_url =original_url ,
    title =title ,
    expires_at =expires_at ,
    custom_code =custom_code ,
    )
    if error :

        status =409 if "already taken"in error or "already exists"in error else 400 
        return jsonify ({"error":"Validation Error","message":error }),status 
    return jsonify ({"url":url_obj .to_dict ()}),201 

@urls_bp .route ("/urls",methods =["GET"])
def get_urls ():
    """
    List URLs with pagination.
    Query params:
      page     (int, default=1)
      per_page (int, default=20, max=100)
      search   (str, optional)
    Response:
      200 — { "urls": [...], "page": 1, "per_page": 20, "total": N, "pages": N }
    """
    try :
        page =max (1 ,int (request .args .get ("page",1 )))
        per_page =min (100 ,max (1 ,int (request .args .get ("per_page",20 ))))
    except ValueError :
        page ,per_page =1 ,20 
    search =request .args .get ("search","").strip ()
    result =list_urls (page =page ,per_page =per_page ,search =search )
    return jsonify (result ),200 

@urls_bp .route ("/urls/<string:short_code>",methods =["GET"])
def get_url (short_code :str ):
    """
    Retrieve metadata for a specific short URL.
    Response:
      200 — {"url": {...}}
      404 — {"error": "Not Found", ...}
    """
    url =get_url_by_code (short_code )
    if url is None :
        return jsonify ({"error":"Not Found","message":"Short URL not found."}),404 
    return jsonify ({"url":url .to_dict ()}),200 

@urls_bp .route ("/urls/<string:short_code>",methods =["DELETE"])
def remove_url (short_code :str ):
    """
    Soft-delete a short URL.
    Response:
      200 — {"message": "URL deleted successfully."}
      404 — {"error": "Not Found", ...}
    """
    success ,error =delete_url (short_code )
    if not success :
        return jsonify ({"error":"Not Found","message":error }),404 
    return jsonify ({"message":"URL deleted successfully."}),200 