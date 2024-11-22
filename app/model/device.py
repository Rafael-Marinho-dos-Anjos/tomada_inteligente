from app import db


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement='auto', nullable = False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(64), nullable=False)
    token = db.Column(db.String(4), nullable=False, unique=True)
