import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'chatbot.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
