"""
wsgi.py - WSGI entry point for production deployment (Gunicorn / Render / Railway).
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
