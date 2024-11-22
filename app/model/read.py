from app import db


class Read(db.Model):
    id_device = db.Column(db.Integer, primary_key=True, nullable = False)
    date_time = db.Column(db.DateTime, primary_key=True, nullable=False)
    fp = db.Column(db.Float, nullable=False)
    s = db.Column(db.Float, nullable=False)
    corr = db.Column(db.Float, nullable=False)
    freq = db.Column(db.Float, nullable=False)
