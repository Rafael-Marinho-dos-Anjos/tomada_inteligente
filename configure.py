from app import app, db
from app.model.device import Device
from app.model.read import Read
from app.model.user import User


with app.app_context():
    db.create_all()
