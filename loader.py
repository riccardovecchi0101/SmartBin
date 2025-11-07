import paho.mqtt.client as mqtt
import json
from models import db, Inserviente, Bidone
from flask import current_app


print("[DEBUG] mqtt_listener importato")

def mqtt_listener(app):
    print("Starting MQTT listener...")
    def on_connect(client, userdata, flags, rc):
        print(f" Connesso al broker (code {rc})")
        if rc == 0:
            with app.app_context():
                inservienti = Inserviente.query.all()
                print(f" Trovati {len(inservienti)} inservienti nel DB")
                for ins in inservienti:
                    topic = f"{ins.citta}/bins/+"
                    print(f"Mi iscrivo a: {topic}")
                    client.subscribe(topic)
        else:
            print("Errore connessione al broker MQTT")

    def on_message(client, userdata, msg):
        print(f"Messaggio ricevuto su {msg.topic}: {msg.payload}")
        try:
            payload = json.loads(msg.payload.decode())
            citta = msg.topic.split("/")[0]
            bidone_id = int(payload['id'])

            with app.app_context():
                inserviente = Inserviente.query.filter_by(citta=citta).all()
                if not inserviente:
                    return

                bidone = Bidone.query.filter_by(id=bidone_id).first()

                if bidone:
                    bidone.weight = payload['weight']
                    bidone.distance = payload['distance']
                    bidone.is_full = payload['is_full']
                    bidone.latitude = payload['latitude']
                    bidone.longitude = payload['longitude']
                    bidone.tipo = payload['tipo']
                    bidone.fulness = payload['percentage']
                    #bidone.citta = payload['citta']

                else:
                    bidone = Bidone(
                        id=bidone_id,
                        weight=payload['weight'],
                        distance=payload['distance'],
                        is_full=payload['is_full'],
                        latitude=payload['latitude'],
                        longitude=payload['longitude'],
                        tipo=payload['tipo'],
                        fulness=payload['percentage'],
                        citta=payload['citta']

                    )
                    db.session.add(bidone)

                db.session.commit()
                print(f"Bidone {bidone.id} aggiornato")

                # CONTROLLO ANOMALIE

              
        except Exception as e:
            print(f"Errore nel processing del messaggio: {e}")

    client = mqtt.Client(client_id="server-listener")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_forever()