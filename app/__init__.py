"""Application factory for the URL shortener."""

from flask import Flask ,jsonify 

from config import config_map 
from app .extensions import db ,limiter ,migrate 


def create_app (config_name :str ="default")->Flask :
    """Create and configure a Flask application instance."""
    app =Flask (__name__ )
    app .config .from_object (config_map .get (config_name ,config_map ["default"]))

    db .init_app (app )
    limiter .init_app (app )
    migrate .init_app (app ,db )

    from app .routes .analytics import analytics_bp 
    from app .routes .main import main_bp 
    from app .routes .redirect import redirect_bp 
    from app .routes .redirect import RegexConverter 
    from app .routes .urls import urls_bp 

    app .url_map .converters ["regex"]=RegexConverter 
    app .register_blueprint (main_bp )
    app .register_blueprint (urls_bp ,url_prefix ="/api")
    app .register_blueprint (analytics_bp ,url_prefix ="/api")
    app .register_blueprint (redirect_bp )

    with app .app_context ():
        from app .models import ClickEvent ,URL 

        db .create_all ()

    @app .errorhandler (400 )
    def bad_request (error ):
        return jsonify ({"error":"Bad Request","message":str (error .description )}),400 

    @app .errorhandler (404 )
    def not_found (error ):
        return jsonify ({"error":"Not Found","message":str (error .description )}),404 

    @app .errorhandler (409 )
    def conflict (error ):
        return jsonify ({"error":"Conflict","message":str (error .description )}),409 

    @app .errorhandler (429 )
    def rate_limited (error ):
        return jsonify ({
        "error":"Too Many Requests",
        "message":"Rate limit exceeded. Please slow down.",
        }),429 

    @app .errorhandler (500 )
    def internal_error (error ):
        return jsonify ({
        "error":"Internal Server Error",
        "message":"An unexpected error occurred.",
        }),500 

    return app 
