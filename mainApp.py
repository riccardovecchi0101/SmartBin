import secrets
import paho
import json
import threading

import time

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_migrate import Migrate

from models import *
from loader import *

secret_key = secrets.token_hex(16)  # good for develop, bad for production (ma stica)

app = Flask("mainApp")
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


@app.errorhandler(404)
def handle_404(e):
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

        return redirect(url_for('signup', uuid=uuid_input))

    return render_template('firstAccess.html')


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    uuid = request.args.get('uuid')
    inserviente = Inserviente.query.filter_by(uuid=uuid).first()

    if not uuid:
        flash("UUID mancante. Inserisci il tuo UUID per registrarti.", "danger")

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        surname = request.form.get('surname')

        if Inserviente.query.filter_by(username=username).first():
            flash("Username già in uso!", "danger")
            return redirect(url_for('signup', uuid=uuid))

        inserviente.name = name
        inserviente.surname = surname
        inserviente.username = username
        inserviente.set_password(password)
        db.session.commit()

        flash("Registrazione completata.", "success")
        return redirect(url_for('index'))

    return render_template('signup.html', uuid=uuid)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        inserviente = Inserviente.query.filter_by(username=username).first()

        if not inserviente or not inserviente.check_password(password):
            flash("Credenziali non valide.", "warning")
            return redirect(url_for('login'))

        session['user_id'] = inserviente.id
        flash(f"Benvenuto, {inserviente.username}!", "success")
        return redirect(url_for('dashboard', uuid=inserviente.uuid))

    return render_template('login.html')


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route("/dashboard/")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for('login'))

    inserviente = Inserviente.query.get(session['user_id'])
    bin_list = Bidone.query.filter(Bidone.inserviente_id == inserviente.id).all()

    return render_template("dashboard.html", inserviente=inserviente, bin_list=bin_list)


@app.route("/refresh_bins", methods=['GET'])
def refresh_bins():
    if "user_id" not in session:
        return jsonify({"error": "Non autorizzato"}), 401

    inserviente = Inserviente.query.get(session['user_id'])
    bin_list = Bidone.query.filter(Bidone.inserviente_id == inserviente.id).all()

    bin_data = [{
        "id": b.id,
        "weight": b.weight,
        "distance": b.distance,
        "tipo": b.tipo,
        "edificio": b.edificio,
        "is_full": b.is_full,
        "fulness": b.fulness
    } for b in bin_list]

    return jsonify(bin_data)


@app.route("/maps")
def maps():
    if "user_id" not in session:
        return redirect(url_for('login'))

    inserviente = Inserviente.query.get(session['user_id'])
    bin_list = Bidone.query.filter(Bidone.inserviente_id == inserviente.id).all()

    bin_dicts = [{
        "id": b.id,
        "weight": b.weight,
        "distance": b.distance,
        "floor": b.floor,
        "is_full": b.is_full,
        "latitude": b.latitude,
        "longitude": b.longitude
    } for b in bin_list if b.latitude is not None and b.longitude is not None]

    return render_template("maps.html", bin_list=bin_dicts)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        t = threading.Thread(target=mqtt_listener, args=(app,))
        t.daemon = True
        t.start()

    app.run(debug=True)
