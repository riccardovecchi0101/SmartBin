import paho.mqtt.client as mqtt
import time

def receive_message(topic="my/test/giuseppe", timeout_sec=10):
    messaggio = None

    def on_connect(client, userdata, flags, rc):
        client.subscribe(topic)

    def on_message(client, userdata, msg):
        messaggio = msg.payload.decode()
        client.disconnect()

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)

    client.loop_start()

    timeout = time.time() + timeout_sec
    while messaggio is None and time.time() < timeout:
        time.sleep(0.1)

    client.loop_stop()

    return messaggio

