import secrets
import paho
import json
import threading
import time

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_migrate import Migrate

from models import *
from loader import *


print("[DEBUG] mainApp importato")
secret_key = secrets.token_hex(16)

app = Flask("mainApp")
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

allowed_uid = ["c530fed9-0c82-44a4-bc20-23d1891d2ff6"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Effettua il login per accedere a questa pagina.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/index")
def index():
    return home()

@app.errorhandler(404)
def handle_404(e):
    return home()

@app.route("/firstAccess", methods=["GET", "POST"])
def firstAccess():
    if request.method == "POST":
        uuid_input = request.form.get("uuid")
        inserviente = Inserviente.query.filter_by(uuid=uuid_input).first()
        print(uuid_input)

        if uuid_input not in allowed_uid:
            flash("UUID non valido!", "danger")
            return redirect(url_for("firstAccess"))

        if inserviente:
            flash("UUID già registrato. Effettua il login.", "warning")
            return redirect(url_for("login"))
        
        new_ins = Inserviente(uuid=uuid_input)
        db.session.add(new_ins)
        db.session.commit()

        return redirect(url_for("signup", uuid=uuid_input))

    return render_template("firstAccess.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    uuid = request.args.get("uuid")
    inserviente = Inserviente.query.filter_by(uuid=uuid).first()

    if not uuid:
        flash("UUID mancante. Inserisci il tuo UUID per registrarti.", "danger")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        surname = request.form.get("surname")
        citta = request.form.get("citta")

        if Inserviente.query.filter_by(username=username).first():
            flash("Username già in uso!", "danger")
            return redirect(url_for("signup", uuid=uuid))

        inserviente.name = name
        inserviente.surname = surname
        inserviente.username = username
        inserviente.set_password(password)
        inserviente.citta = citta 
        db.session.commit()

        flash("Registrazione completata.", "success")
        return redirect(url_for("index"))

    return render_template("signup.html", uuid=uuid)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        inserviente = Inserviente.query.filter_by(username=username).first()

        if not inserviente or not inserviente.check_password(password):
            flash("Credenziali non valide.", "warning")
            return redirect(url_for("login"))

        session["user_id"] = inserviente.id
        flash(f"Benvenuto, {inserviente.username}!", "success")
        return redirect(url_for("dashboard", uuid=inserviente.uuid))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

@app.route("/dashboard/")
@login_required
def dashboard():
    inserviente = Inserviente.query.get(session["user_id"])
    bin_list = Bidone.query.filter(Bidone.citta == inserviente.citta).all()
    return render_template("dashboard.html", inserviente=inserviente, bin_list=bin_list)

@app.route("/refresh_bins", methods=["GET"])
@login_required
def refresh_bins():
    inserviente = Inserviente.query.get(session["user_id"])
    bin_list = Bidone.query.filter(Bidone.citta == inserviente.citta).all()

    bin_data = [{
        "id": b.id,
        "weight": b.weight,
        "distance": b.distance,
        "is_full": b.is_full,
        "latitude": b.latitude,
        "longitude": b.longitude,
        "fulness": b.fulness,
        "tipo": b.tipo,
        "citta": b.citta
    } for b in bin_list]

    return jsonify(bin_data)

@app.route("/maps")
@login_required
def maps():
    inserviente = Inserviente.query.get(session["user_id"])
    bin_list = Bidone.query.filter(Bidone.citta == inserviente.citta).all()

    bin_dicts = [{
        "id": b.id,
        "weight": b.weight,
        "distance": b.distance,
        "is_full": b.is_full,
        "latitude": b.latitude,
        "longitude": b.longitude,
        "fulness": b.fulness,
        "tipo": b.tipo,
        "citta": b.citta
    } for b in bin_list if b.latitude is not None and b.longitude is not None]

    return render_template("maps.html", bin_list=bin_dicts)




if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    t = threading.Thread(target=mqtt_listener, args=(app,))
    t.daemon = True
    t.start()

    app.run(debug=True, use_reloader=False)
