import json
import paho.mqtt.client as mqtt
import serial
import time

# Apro la porta seriale (modifica il nome se necessario)
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

# Configurazione del broker MQTT pubblico di Mosquitto
BROKER = "test.mosquitto.org"
PORT = 1883

# Topic MQTT
TOPIC_PUB = "Modena/bins/1"           # Topic per pubblicare i dati dal cestino
TOPIC_CMD = "5/anomaly"               # Topic per ricevere comandi/anomalie

# Creo un client MQTT
client = mqtt.Client()

tipo = "carta"     # tipo simulato
citta = "Modena"   # città simulata

# Funzione eseguita quando il client si connette al broker
def on_connect(client, userdata, flags, rc):
    print("Connesso al broker MQTT")
    client.subscribe(TOPIC_PUB)
    print(f"Iscritto al topic dei comandi: {TOPIC_PUB}")

# Funzione eseguita quando ricevo un messaggio da un topic sottoscritto
def on_message(client, userdata, msg):
    comando = msg.payload.decode('utf-8')
    print(f"Ricevuto comando da MQTT: {comando}")
    ser.write((comando + "\n").encode())

# Associo le funzioni di callback al client MQTT
client.on_connect = on_connect
client.on_message = on_message

# Connessione al broker
client.connect(BROKER, PORT, 60)
client.loop_start()

# Funzione che legge continuamente dalla seriale e pubblica su MQTT
def read_serial_data():
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            try:
                items = line.split(",")
                data = {}
                for item in items:
                    if ":" in item:
                        key, value = item.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "is_full":
                            data[key] = bool(int(value))
                        elif key in ["id", "floor", "weight", "distance", "fulness"]:
                            try:
                                num_value = float(value)
                                data[key] = abs(num_value)
                            except ValueError:
                                data[key] = value
                        elif key in ["latitude", "longitude"]:
                            try:
                                data[key] = float(value)
                            except ValueError:
                                data[key] = value
                        elif key in ["edificio", "tipo"]:
                            data[key] = value
                        else:
                            data[key] = value

                if data:
                    data["tipo"] = tipo
                    data["citta"] = citta
                    json_data = json.dumps(data)
                    client.publish(TOPIC_PUB, json_data, retain=True)
                    print(f"Pubblicato su MQTT: {json_data}")
                else:
                    print(f"Dati non validi ricevuti: {line}")

            except Exception as e:
                print(f"Errore nella conversione dei dati: {e}")

        time.sleep(0.1)

# Punto d'ingresso del programma
if __name__ == "__main__":
    print("Avvio del gateway seriale↔MQTT")
    read_serial_data()
