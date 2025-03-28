import secrets

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate

from models import *

secret_key = secrets.token_hex(16)  # good for develop, bad for production (ma stica)

app = Flask("SmartBin")
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


@app.route("/")  # app route si riferisce direttamente alla funzione
def home():
    return render_template('index.html')


@app.route("/index")
def index():
    return home()


@app.route("/firstAccess", methods=['GET', 'POST'])
def firstAccess():
    if request.method == 'POST':
        uuid_input = request.form.get('uuid')
        inserviente = Inserviente.query.filter_by(uuid=uuid_input).first()

        if not inserviente:
            flash("UUID non valido!", "danger")
            return redirect(url_for('firstAccess'))

        if inserviente.username:
            flash("UUID già registrato. Effettua il login.", "warning")
            return redirect(url_for('login'))

        return redirect(url_for('signup'))

    return render_template('firstAccess.html')


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
