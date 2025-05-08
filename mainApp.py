import secrets
import paho
import json

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


def check_is_full(bin):
    try:
        return float(bin.weight) > 18 and float(bin.distance) < 20
    except:
        return False


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

    topic = str(inserviente.uuid) + '/test2'
    message = receive_message(topic=topic)

    if message is not None:
        payload_dict = json.loads(message)  # Converti di nuovo in dizionario
        bidone_id = int(payload_dict['id'])
        bin = Bidone.query.filter(
            Bidone.inserviente_id == inserviente.id,
            Bidone.id == bidone_id
        ).first()

        if bin:
            bin.floor = payload_dict['floor']
            bin.weight = payload_dict['weight']
            bin.distance = payload_dict['distance']
            bin.is_full = check_is_full(bin)
            bin.latitude = payload_dict['latitude']
            bin.longitude = payload_dict['longitude']

        else:
            bin = Bidone(
                id=bidone_id,
                inserviente=inserviente,
                floor=payload_dict['floor'],
                weight=payload_dict['weight'],
                distance=payload_dict['distance'],
                is_full=payload_dict['is_full'],
                latitude=payload_dict['latitude'],
                longitude=payload_dict['longitude']
            )
            db.session.add(bin)

        db.session.commit()

        anomaly_topic = str(inserviente.uuid) + str(bin.id) + '/anomaly'

        if bin.weight is None or bin.distance is None:
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Nessun valore misurato")

        if (float(bin.weight) > 15 and float(bin.distance) > 30) or (
                float(bin.weight) < 5 and float(bin.distance) < 60):
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Valori misurati inconsistenti. Controllare il bidone")

        if float(bin.weight) > 18 and float(bin.distance) < 20:
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Bidone pieno")

    else:
        print("Non ho ricevuto nulla entro il timeout")

    bin_list = Bidone.query.filter(Bidone.inserviente_id == inserviente.id).all()

    return render_template("dashboard.html", inserviente=inserviente, bin_list=bin_list)


@app.route("/refresh_bins", methods=['GET'])
def refresh_bins():
    if "user_id" not in session:
        return jsonify({"error": "Non autorizzato"}), 401

    print(f"User ID: {session.get('user_id')}")

    inserviente = Inserviente.query.get(session['user_id'])
    topic = f"{inserviente.uuid}/test2"
    message = receive_message(topic=topic)

    if message:
        payload_dict = json.loads(message)
        bidone_id = int(payload_dict['id'])
        bin = Bidone.query.filter(
            Bidone.inserviente_id == inserviente.id,
            Bidone.id == bidone_id
        ).first()

        if bin:
            bin.floor = payload_dict['floor']
            bin.weight = payload_dict['weight']
            bin.distance = payload_dict['distance']
            bin.is_full = check_is_full(bin)
            bin.latitude = payload_dict['latitude']
            bin.longitude = payload_dict['longitude']
        else:
            bin = Bidone(
                id=bidone_id,
                inserviente=inserviente,
                floor=payload_dict['floor'],
                weight=payload_dict['weight'],
                distance=payload_dict['distance'],
                is_full=payload_dict['is_full'],
                latitude=payload_dict['latitude'],
                longitude=payload_dict['longitude'],
            )
            db.session.add(bin)

        db.session.commit()

        if bin.is_full and bin.latitude and bin.longitude:
            all_bins = Bidone.query.filter(
                Bidone.inserviente_id == inserviente.id,
                Bidone.id != bin.id
            ).all()

        def distanceBin(b):
            try:
                return ((float(b.latitude) - float(bin.latitude)) ** 2 +
                        (float(b.longitude) - float(bin.longitude)) ** 2) ** 0.5
            except:
                return float('inf')

        empty_bins = [b for b in all_bins if not b.is_full and b.latitude and b.longitude]
        if empty_bins:
            nearest_bins = min(empty_bins, key=distanceBin)
            msg = json.dumps({
                "messaggio": f"Raggiungi il cestino {nearest_bins.id}"
            })
            topic_lcd = f"{inserviente.uuid}/test2"
            # publish_message(topic_lcd, msg)

        anomaly_topic = str(inserviente.uuid) + str(bin.id) + '/test2'
        if bin.weight is None or bin.distance is None:
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Nessun valore misurato")

        if (bin.weight > 15 and bin.distance > 30) or (bin.weight < 5 and bin.distance < 60):
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Valori misurati inconsistenti. Controllare il bidone")

        if bin.weight > 18 and bin.distance < 20:
            print("segnalo anomalia")
            send_anomaly(anomaly_topic, "Bidone pieno")

    bin_list = Bidone.query.filter(Bidone.inserviente_id == inserviente.id).all()
    bin_data = [{
        "id": b.id,
        "weight": b.weight,
        "distance": b.distance,
        "floor": b.floor,
        "is_full": b.is_full
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


@app.route("/update_bins", methods=['POST'])
def update_bins():
    bins_data = {
        "bins": [
            {"id": 1, "status": "Pieno"},
            {"id": 2, "status": "Vuoto"},
            {"id": 3, "status": "Quasi Pieno"},
        ]
    }

    return jsonify(bins_data)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
