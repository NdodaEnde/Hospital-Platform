"""
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
# Import app from app.py
from app import app

# Initialize SQLAlchemy without passing the app parameter
db = SQLAlchemy()
ma = Marshmallow(app)
"""

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask import Flask

db = SQLAlchemy()
ma = Marshmallow()

def init_app(app: Flask):
    db.init_app(app)
    ma.init_app(app)
