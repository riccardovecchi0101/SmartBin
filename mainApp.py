from flask import Flask
from flask import render_template
from flask_migrate import Migrate
from models import db, Utente

import secrets

secret_key = secrets.token_hex(16) #good for develop, bad for production (ma stica)
app.config['SECRET_KEY'] = secret_key

app = Flask("SmartBin")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db) 

@app.route("/") #app route si riferisce direttamente alla funzione
def home():
    return render_template('index.html')

@app.route("/index/")
def index():
    return home()

@app.route("/prova")
def prova():
    return "<html><b> Pagina di prova <b></html>"

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)