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
TOPIC_PUB = "730af27a-9586-4ba5-add1-24ea7deef188/bins"           # Topic per pubblicare i dati dal cestino
TOPIC_CMD = "5/anomaly"       # Topic per ricevere comandi/anomalie

# Creo un client MQTT
client = mqtt.Client()

# Funzione eseguita quando il client si connette al broker
def on_connect(client, userdata, flags, rc):
    print("Connesso al broker MQTT")
    # Mi iscrivo al topic dei comandi (es. chiudi cestino, anomalie, ecc.)
    client.subscribe(TOPIC_PUB)
    print(f"Iscritto al topic dei comandi: {TOPIC_PUB}")

# Funzione eseguita quando ricevo un messaggio da un topic sottoscritto
def on_message(client, userdata, msg):
    # Decodifico il messaggio ricevuto
    comando = msg.payload.decode('utf-8')
    print(f"Ricevuto comando da MQTT: {comando}")
    # Inoltro il comando ad Arduino via seriale
    ser.write((comando + "\n").encode())

# Associo le funzioni di callback al client MQTT
client.on_connect = on_connect
client.on_message = on_message

# Connessione al broker
client.connect(BROKER, PORT, 60)

# Avvio il loop MQTT in un thread separato
client.loop_start()

# Funzione che legge continuamente dalla seriale e pubblica su MQTT
def read_serial_data():
    while True:
        if ser.in_waiting > 0:
            # Leggo una linea dalla seriale
            line = ser.readline().decode('utf-8').strip()
            try:
                # Converto i dati da stringa a dizionario
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
                                data[key] = int(value)
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

                
                # Se i dati sono validi, li invio al topic MQTT
                if data:
                    json_data = json.dumps(data)
                    client.publish(TOPIC_PUB, json_data,retain=True)
                    print(f"Pubblicato su MQTT: {json_data}")
                else:
                    print(f"Dati non validi ricevuti: {line}")

            except Exception as e:
                print(f"Errore nella conversione dei dati: {e}")

        time.sleep(0.1)  # Piccola pausa per evitare sovraccarico del loop

# Punto d'ingresso del programma
if __name__ == "__main__":
    print("Avvio del gateway seriale↔MQTT")
    read_serial_data()