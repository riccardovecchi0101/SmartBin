import paho.mqtt.client as mqtt
import json
import time
import random
from paho.mqtt.client import CallbackAPIVersion

BROKER = "test.mosquitto.org"
PORT = 1883

# Creo il client MQTT
client = mqtt.Client(CallbackAPIVersion.VERSION1, client_id="bidone-simulator")
client.connect(BROKER, PORT, 60)
client.loop_start()

tipi = ["carta", "plastica", "indifferenziato"]

def genera_messaggio(bidone_id):
    return {
        "id": bidone_id,
        "floor": random.randint(1, 3),
        "percentage": f"{random.uniform(0.0, 100.0):.2f}",
        "weight": f"{random.uniform(0.0, 20.0):.2f}",
        "distance": f"{random.uniform(10.0, 100.0):.2f}",
        "is_full": random.choice([True, False]),
        "latitude": round(random.uniform(44.6, 44.7), 6),
        "longitude": round(random.uniform(10.9, 11.1), 6),
        "tipo": random.choice(tipi),
        "citta": "Modena"
    }

try:
    while True:
        for bidone_id in range(2, 4):  # Simula 3 bidoni
            topic = f"Modena/bins/{bidone_id}"
            payload = json.dumps(genera_messaggio(bidone_id))
            client.publish(topic, payload, retain=True)
            print(f"📤 Pubblicato su {topic}: {payload}")
        time.sleep(20)
except KeyboardInterrupt:
    print("Interrotto manualmente.")
finally:
    client.loop_stop()
    client.disconnect()
