from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()


class Inserviente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    surname = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=True)
    piano = db.Column(db.String(10), nullable=True)
    password = db.Column(db.String(100), nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<Inserviente {self.name}, >" + ":" + " " + "UUID:" + self.uuid
