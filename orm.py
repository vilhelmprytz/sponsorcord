from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

db = SQLAlchemy()


class Sponsor(db.Model):
    github_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    discord_id = db.Column(db.BigInteger, unique=True)

    time_created = db.Column(db.DateTime, server_default=func.now())
    time_updated = db.Column(
        db.DateTime, server_default=func.now(), onupdate=func.now()
    )
