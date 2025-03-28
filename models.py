from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Inserviente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    surname = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=True)
    piano = db.Column(db.String(10), nullable=True)
    password = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<Inserviente {self.name}, >" + ":" + " " + "UUID:" + self.uuid
