"""
app/routes/main.py — HTML page routes
Renders the three main frontend pages:
  /           → index.html  (landing + URL creation form)
  /dashboard  → dashboard.html (URL management table)
  /analytics  → analytics.html (charts and stats)
"""
from flask import Blueprint ,render_template 
main_bp =Blueprint ("main",__name__ )
@main_bp .route ("/")
def index ():
    """Landing page with the URL shortening form."""
    return render_template ("index.html")
@main_bp .route ("/dashboard")
def dashboard ():
    """URL management interface."""
    return render_template ("dashboard.html")
@main_bp .route ("/analytics")
def analytics ():
    """Analytics charts and statistics."""
    return render_template ("analytics.html")
