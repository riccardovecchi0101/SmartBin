import json
import paho.mqtt.client as mqtt
import serial
import time

# Porta seriale Arduino
SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUDRATE = 9600

# Broker MQTT
BROKER = "broker.emqx.io"
PORT = 1883

tipo = "carta"  # tipo simulato
citta = "Modena"  # città simulata
BIN_ID = 1

# Topic MQTT
TOPIC_PUB = f"{citta}/bins/{BIN_ID}"         # Arduino -> backend
TOPIC_LCD = f"{citta}/bins/{BIN_ID}/lcd"     # messaggi LCD -> Arduino
TOPIC_CMD = f"{citta}/bins/{BIN_ID}/cmd"     # comandi remoti -> Arduino
TOPIC_ANOMALIES = f"{citta}/bins/{BIN_ID}/anomalies" # anomalie -> Arduino

# Serial
ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)

# Creo un client MQTT
client = mqtt.Client()


# Funzione eseguita quando il client si connette al broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Connesso al broker MQTT")
        client.subscribe(TOPIC_LCD)
        client.subscribe(TOPIC_CMD)
        client.subscribe(TOPIC_ANOMALIES)
        print(f"[MQTT] Iscritto al topic LCD: {TOPIC_LCD}")
        print(f"[MQTT] Iscritto al topic CMD: {TOPIC_CMD}")
        print(f"[MQTT] Iscritto al topic ANOMALIES: {TOPIC_ANOMALIES}")
    else:
        print(f"[MQTT] Connessione fallita con codice {rc}")


# Funzione eseguita quando ricevo un messaggio da un topic sottoscritto
def on_message(client, userdata, msg):
    try:
        payload_raw = msg.payload.decode('utf-8')
        print(f"[MQTT] Messaggio ricevuto su {msg.topic}: {payload_raw}")

        # Se è un messaggio per LCD, lo inoltro così com'è
        if msg.topic == TOPIC_LCD:
            ser.write((payload_raw + "\n").encode("utf-8"))
            print(f"[SERIAL] Inviato ad arduino per LCD")
        
        # Se è un comando, lo trasformo in una riga tipo "CMD:FORCE_OPEN"
        elif msg.topic == TOPIC_CMD:
            try:
                data = json.loads(payload_raw)
                cmd = data.get("cmd", "").strip().upper()
            except Exception:
                cmd = payload_raw.strip().upper()
            
            if cmd:
                line = f"CMD:{cmd}\n"
                ser.write(line.encode("utf-8"))
                print(f"[SERIAL] Inviato comando ad arduino: {line.strip()}")
        
        # Se è un'a'nomalia, la trasformo in un messaggio LCD
        elif msg.topic == TOPIC_ANOMALIES:
            try:
                data = json.loads(payload_raw)
                anomaly_type = str(data.get("type", "Anomalia"))

                lcd_text = f"Anomalia: {anomaly_type}"

                lcd_payload = json.dumps({
                    "messagge": lcd_text,
                    "timestamp": int(time.time()),
                })

                ser.write((lcd_payload + "\n").encode("utf-8"))
                print(f"[SERIAL] Inviato messaggio ANOMALIA ad arduino come LCD: {lcd_payload}")
            except Exception as e:
                print(f"[MQTT] Errore nel parsing del messaggio ANOMALIA: {e}")
                
    except Exception as e:
        print(f"[MQTT] Errore in on_message")


# Associo le funzioni di callback al client MQTT
client.on_connect = on_connect
client.on_message = on_message


def parse_serial_line(line: str):
    """
    Converte una riga del tipo:
    id:1,floor:0,percentage:0.00,weight:0.00,distance:25.00,is_full:0,latitude:44.111111,longitude:11.222222

    in un dizionario Python, aggiungendo `citta` e `tipo`.
    """
    line =  line.strip()
    if not line:
        return None
    
    parts = line.split(",")
    raw = {}

    for part in parts:
        if ':' not in part:
            continue
        key, value = part.split(':', 1)
        key = key.strip()
        value = value.strip()
        if key:
            raw[key] = value
    
    # Se manca l'id, non ha senso proseguire
    if "id" not in raw:
        print(f"[PARSE] Nessun id nella riga: {line}")
        return None
    
    try:
        payload = {
            "id": int(raw.get("id", BIN_ID)),
            "floor": int(raw.get("floor", 0)),
            "percentage": float(raw.get("percentage", 0.0)),
            "weight": float(raw.get("weight", 0.0)),
            "distance": float(raw.get("distance", 0.0)),
            "is_full": True if raw.get("is_full", "0") == "1" else False,
            "latitude": float(raw.get("latitude", 0.0)),
            "longitude": float(raw.get("longitude", 0.0)),
            "citta": citta,
            "tipo": tipo,
        }
    except Exception as e:
        print(f"[PARSE] Errore nella conversione dei dati: {e} | linea: {line}")
        return None

    return payload


# Funzione che legge continuamente dalla seriale e pubblica su MQTT
def read_serial_and_publish():
    """
    Legge continuamente dalla seriale, fa il parsing e pubblica su MQTT.
    """

    while True:
        try:
            if ser.in_waiting > 0:
                line_bytes = ser.readline()
                try:
                    line = line_bytes.decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = ""
                if not line:
                    continue

                print(f"[SERIAL] Ricevuto: {line}")
                payload = parse_serial_line(line)
                if payload is not None:
                    json_data = json.dumps(payload)
                    result = client.publish(TOPIC_PUB, json_data, retain=True, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print(f"[MQTT] Pubblicato su {TOPIC_PUB}: {json_data}")
                    else:
                        print(f"[MQTT] Errore publish: rc = {result.rc}")
                else:
                    print(f"[SERIAL] Dati non validi, ignorata")

            # Piccola pausa per evitare di sovraccaricare la CPU
            time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("Interruzione da tastiera, chiusura...")
            break
        except Exception as e:
            print(f"[LOOP] Errore nel loop principale: {e}")
            time.sleep(0.5)


# Punto d'ingresso del programma
if __name__ == "__main__":
    print("Avvio del gateway seriale ↔ MQTT")
    print(f"  Serial: {SERIAL_PORT} @ {SERIAL_BAUDRATE}")
    print(f"  Broker: {BROKER}:{PORT}")
    print(f"  Bidone: id={BIN_ID}, tipo={tipo}, citta={citta}")
    print(f"  Topic dati: {TOPIC_PUB}")
    print(f"  Topic LCD:  {TOPIC_LCD}")
    print(f"  Topic CMD:  {TOPIC_CMD}")
    print(f"  Topic ANOMALIES: {TOPIC_ANOMALIES}")

    # Connessione MQTT
    client.connect(BROKER, PORT, keepalive=60)
    # Thread interno per gestire la rete MQTT
    client.loop_start()

    # Loop di lettura seriale e publish
    read_serial_and_publish()
    
    # Se esco dal loop principale, fermo il client MQTT
    client.loop_stop()
    client.disconnect()
    ser.close()
