from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Utente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    cognome = db.Column(db.String(100))
    UUID = db.Column(db.String(36))
    password = db.Column(db.String(25))

    def __repr__(self):
        return f"<Utente {self.nome}, >"+ ":"+ " "+ "UUID:" +self.UUID