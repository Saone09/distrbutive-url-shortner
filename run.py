"""Development server entry point. Run with ``python run.py``."""
import os 
from app import create_app 

env =os .environ .get ("FLASK_ENV","development")
app =create_app (env )
if __name__ =="__main__":
    app .run (
    host =os .environ .get ("HOST","127.0.0.1"),
    port =int (os .environ .get ("PORT",5000 )),
    debug =app .config .get ("DEBUG",False ),
    )