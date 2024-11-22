from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement='auto', nullable = False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    login = db.Column(db.String(64), nullable=False, unique=True)
    psswrd = db.Column(db.String(64), nullable=False)
