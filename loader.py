import paho.mqtt.client as mqtt
import json
from models import db, Inserviente, Bidone
from flask import current_app


def mqtt_listener(app):

    def on_connect(client, userdata, flags, rc):
        print(f" Connesso al broker (code {rc})")
        if rc == 0:
            with app.app_context():
                inservienti = Inserviente.query.all()
                print(f" Trovati {len(inservienti)} inservienti nel DB")
                for ins in inservienti:
                    topic = f"{ins.uuid}/bins/#"
                    print(f"Mi iscrivo a: {topic}")
                    client.subscribe(topic)
        else:
            print("Errore connessione al broker MQTT")

    def on_message(client, userdata, msg):
        print(f"Messaggio ricevuto su {msg.topic}: {msg.payload}")
        try:
            payload = json.loads(msg.payload.decode())
            uuid = msg.topic.split("/")[0]
            bidone_id = int(payload['id'])

            with app.app_context():
                inserviente = Inserviente.query.filter_by(uuid=uuid).first()
                if not inserviente:
                    print(f"UUID {uuid} non trovato nel DB")
                    return

                bidone = Bidone.query.filter_by(id=bidone_id, inserviente_id=inserviente.id).first()

                if bidone:
                    bidone.weight = payload['weight']
                    bidone.distance = payload['distance']
                    bidone.is_full = payload['is_full']
                    bidone.latitude = payload['latitude']
                    bidone.longitude = payload['longitude']
                    bidone.tipo = payload['tipo']
                    bidone.edificio = payload['edificio']
                    bidone.fulness=payload['fulness']

                else:
                    bidone = Bidone(
                        id=bidone_id,
                        inserviente=inserviente,
                        weight=payload['weight'],
                        distance=payload['distance'],
                        is_full=payload['is_full'],
                        latitude=payload['latitude'],
                        longitude=payload['longitude'],
                        tipo=payload['tipo'],
                        edificio=payload['edificio'],
                        fulness=payload['fulness']
                    )
                    db.session.add(bidone)

                db.session.commit()
                print(f"Bidone {bidone.id} aggiornato")

                ##CONTROLLO ANOMALIE##

                weight = float(bidone.weight)
                distance = float(bidone.distance)

                

                anomaly = None

                if (weight > 15 and distance > 45) or (weight < 10 and distance < 45):
                    anomaly = "Dati inconsistenti, controllare il bidone."

                if weight > 20 or distance > 90:
                    anomaly = "Misurazioni errate, controllare il bidone."

                if anomaly:
                    topic = f"{bidone.inserviente.uuid}/{bidone.id}/anomaly"
                    print(f" Pubblico anomalia: {anomaly} su {topic}")
                    client.publish(topic, anomaly, retain=True)


        except Exception as e:
            print(f"Errore nel processing del messaggio: {e}")


    client = mqtt.Client(client_id="server-listener")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_forever()
