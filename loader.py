import paho.mqtt.client as mqtt
import time
import uuid

def receive_message(topic, timeout_sec=5):
    messaggio = None
    ricevuto = False

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connesso al broker")
            client.subscribe(topic)
        else:
            print(f"Connessione fallita. Codice: {rc}")

    def on_message(client, userdata, msg):
        nonlocal messaggio, ricevuto
        messaggio = msg.payload.decode()
        ricevuto = True
        print(f"📨 Ricevuto messaggio: {messaggio}")
        client.disconnect()  # Disconnessione immediata dopo aver ricevuto

    client_id = f"loader-{uuid.uuid4()}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("test.mosquitto.org", 1883, 60)
    client.loop_start()

    # Attendi fino a ricezione o timeout
    start_time = time.time()
    while not ricevuto and (time.time() - start_time) < timeout_sec:
        time.sleep(0.1)

    client.loop_stop()

    return messaggio
