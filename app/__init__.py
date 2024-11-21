import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists, create_database


db = SQLAlchemy()
app = Flask(__name__)

username = "root"
password = "5pror3t2"
host = "localhost"
port = 3306
database_name = "tomadas"

database_url = "mysql://{}:{}@{}:{}/{}".format(
    username, password, host, port, database_name
)

if not database_exists(database_url):
    create_database(database_url)
    import configure

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

# app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
db.init_app(app)
