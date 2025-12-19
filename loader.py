import math
from math import radians, sin, cos, asin, sqrt

import paho.mqtt.client as mqtt
import json

from models import db, Inserviente, Bidone
import time

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

print("[DEBUG] mqtt_listener importato")

def send_bin_command(citta, bidone_id, command):
        """
        Pubblica un comando sul topic:
          <citta>/bins/<id>/cmd
        Esempio:
          Modena/bins/1/cmd  --> {"cmd": "UNLOCKED"}
        """
        topic = f"{citta}/bins/{bidone_id}/cmd"
        payload = {"cmd": command}

        client = mqtt.Client()
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"[CMD] Inviato comando al bidone {bidone_id} ({citta})")
            client.disconnect()
        except Exception as e:
            print(f"[CMD] Errore publish comando {command} a {topic}: {e}")


def haversine_km(lat1, lon1, lat2, lon2):
    # ritorna distanza in km tra due coordinate
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(min(1, sqrt(a)))
    return R * c


def mqtt_listener(app):
    print("Starting MQTT listener...")

    # Soglie di default
    DEFAULT_WEIGHT_THRESHOLD = app.config.get("MQTT_WEIGHT_THRESHOLD", 0.3)
    DEFAULT_DISTANCE_THRESHOLD = app.config.get("MQTT_DISTANCE_THRESHOLD", 10)
    
    DEBOUNCE_SECOND = app.config.get("MQTT_DEBOUNCE_SECOND", 300)
    LCD_DEBOUNCE_SECONDS = app.config.get("LCD_DEBOUNCE_SECONDS", 300)  # evita messaggi LCD ripetuti
    
    EMPTY_PERCENTAGE_THRESHOLD = app.config.get("EMPTY_PERCENTAGE_THRESHOLD", 40)  # considerato "vuoto" se fulness <= 20%
    
    MAX_SEARCH_KM = app.config.get("MAX_NEAREST_SEARCH_KM", 5)  # cerca solo entro 5 km

    # Cache in-memory per limitare spam di anomalie
    last_anomaly_time = {}  # key: (citta, bidone_id, reason) -> timestamp
    last_lcd_time = ({})  # key: (citta, bidone_id) -> timestamp dell'ultimo messaggio lcd inviato

    def debounce(citta, bidone_id, reason, last_map, seconds):
        key = (citta, bidone_id, reason)
        now = time.time()
        last = last_map.get(key, 0)

        if now - last < seconds:
            return True

        last_map[key] = now

        return False

    def publish_anomalies(client, citta, bidone_id, anomaly_type, details):
        if debounce(citta, bidone_id, anomaly_type, last_anomaly_time, DEBOUNCE_SECOND):
            print(f"[ANOMALY] Debounced {anomaly_type} for {citta} bidone {bidone_id} ")
            return

        payload = {
            "id": bidone_id,
            "citta": citta,
            "type": anomaly_type,
            "details": details,
            "timestamp": int(time.time()),
        }
        topic = f"{citta}/bins/{bidone_id}/anomalies"
        try:
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"[ANOMALY] Pubblicata {anomaly_type} per {citta} bin {bidone_id}")

            try:
                send_bin_command(citta, bidone_id, "LOCKED")
                print(f"[ANOMALY] Inviato comando LOCKED al bidone {bidone_id} ({citta})")
            except Exception as e:
                print(f"[ANOMALY] Errore invio comando LOCKED per anomalia: {e}")
        except Exception as e:
            print(f"[ANOMALY] Error publishing anomalies {e}")

    def publish_lcd_message(client, citta, bidone_id, message):
        if debounce(
            citta, bidone_id, "lcd_message", last_lcd_time, LCD_DEBOUNCE_SECONDS
        ):
            print(f"[LCD] Debounced LCD message for {citta} bidone {bidone_id}")
            return
        topic = f"{citta}/bins/{bidone_id}/lcd"
        payload = {"message": message, "timestamp": int(time.time())}
        try:
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"[LCD] Published to {topic}: {payload}")
        except Exception as e:
            print(f"[LCD] Errore publish LCD: {e}")

    def find_nearest_empty_bin(app, current_bin):
        """
        Cerca nel DB il bidone 'vuoto' più vicino al bidone corrente.
        Preferisce usare lat/lon (haversine). Se lat/lon mancanti,
        usa il campo fulness (percentuale) e ritorna un bidone con fulness <= EMPTY_PERCENTAGE_THRESHOLD.
        Restituisce (bidone_obj, distance_km) o (None, None) se non trovato.
        """
        with app.app_context():
            # prendi tutti i bidoni della stessa città tranne quello corrente
            candidates = Bidone.query.filter(
                Bidone.citta == current_bin.citta, Bidone.id != current_bin.id
            ).all()
            best = None
            best_dist = None

            # se il bidone corrente ha lat/lon, usa coordinate
            try:
                cur_lat = (
                    float(current_bin.latitude)
                    if current_bin.latitude is not None
                    else None
                )
                cur_lon = (
                    float(current_bin.longitude)
                    if current_bin.longitude is not None
                    else None
                )
            except Exception:
                cur_lat = cur_lon = None

            if cur_lat is not None and cur_lon is not None:
                for b in candidates:
                    try:
                        if b.latitude is None or b.longitude is None:
                            continue
                        lat2 = float(b.latitude)
                        lon2 = float(b.longitude)
                        dist = haversine_km(cur_lat, cur_lon, lat2, lon2)

                        # consideralo solo se è considerato "vuoto" (is_full False o fulness <= threshold)
                        fulness = None
                        try:
                            fulness = (
                                float(b.fulness) if b.fulness is not None else None
                            )
                        except Exception:
                            fulness = None
                        is_empty = (b.is_full is False) or (
                            fulness is not None
                            and fulness <= EMPTY_PERCENTAGE_THRESHOLD
                        )
                        if not is_empty:
                            continue
                        if dist <= MAX_SEARCH_KM and (best is None or dist < best_dist):
                            best = b
                            best_dist = dist
                    except Exception:
                        continue
            else:
                # fallback: usa fulness/is_full senza coordinate, scegli il più 'vuoto' e con peso/distanza ragionevoli
                for b in candidates:
                    try:
                        fulness = None
                        try:
                            fulness = (
                                float(b.fulness) if b.fulness is not None else None
                            )
                        except Exception:
                            fulness = None
                        if b.is_full is False or (
                            fulness is not None
                            and fulness <= EMPTY_PERCENTAGE_THRESHOLD
                        ):
                            # assegna priorità al fulness più basso; non abbiamo distanza -> dist = None
                            key_metric = fulness if fulness is not None else 100.0
                            if best is None or key_metric < best_dist:
                                best = b
                                best_dist = key_metric
                    except Exception:
                        continue
            return best, best_dist

    def detect_additional_anomalies(payload, bidone_obj):
        """
        Controlli aggiuntivi 'sanity checks' che suggerisco:
        - valori negativi o non numerici
        - valori troppo grandi rispetto al passato (spike)
        - coordinate inconsistenti
        - sensore 'stuck' (stessi valori molte volte)
        - mismatch tra percentage e distance/weight
        Restituisce lista di (type, details)
        """
        anomalies = []

        try:
            weight = float(payload.get("weight", math.nan))
            distance = float(payload.get("distance", math.nan))
            percentage = float(payload.get("percentage", math.nan))
        except Exception:
            anomalies.append(("invalid_format", "Campi numerici non validi"))
            return anomalies

        if math.isnan(weight) or math.isnan(distance):
            anomalies.append(("missing_value", "weight o distance mancante"))
            return anomalies

        if weight < 0 or distance < 0 or percentage < 0:
            anomalies.append((
                "negative_value",
                f"weight={weight}, distance={distance}, percentage={percentage}",
            ))

        # unrealist upper bounds
        if weight > 200:
            anomalies.append(("unrealistic_weight", f"weight troppo alto: {weight}"))

        if distance > 100:
            anomalies.append((
                "unrealistic_distance", f"distance troppo alto: {distance}"
            ))

        # controllo dati storici del bidone
        if bidone_obj and bidone_obj.weight is not None:
            try:
                prev = float(bidone_obj.weight)
                # spike: salto superiore al 200% o simile
                if prev > 0 and abs(weight - prev) / prev > 2.0:
                    anomalies.append(
                        ("sudden_weight_change", f"prev={prev}, now={weight}")
                    )
            except Exception:
                pass

        # posizione: controllo elementare
        lat = payload.get("latitude")
        lon = payload.get("longitude")

        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
                    anomalies.append(("gps_out_of_range", f"lat={lat}, lon={lon}"))
            except Exception:
                anomalies.append(("gps_invalid", f"lat={lat}, lon={lon}"))

        # mismatch logico: percentage alta ma distance grande (vuoto) ecc.
        if percentage >= 80 and distance > DEFAULT_DISTANCE_THRESHOLD * 2:
            anomalies.append(
                (
                    "fulness_distance_mismatch",
                    f"percentage={percentage}, distance={distance}",
                )
            )

        return anomalies

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
            bidone_id = int(payload["id"])

            weight_threshold = app.config.get(
                "MQTT_WEIGHT_THRESHOLD", DEFAULT_WEIGHT_THRESHOLD
            )
            distance_threshold = app.config.get(
                "MQTT_DISTANCE_THRESHOLD", DEFAULT_DISTANCE_THRESHOLD
            )

            with app.app_context():
                inserviente = Inserviente.query.filter_by(citta=citta).all()
                if not inserviente:
                    return

                bidone = Bidone.query.filter_by(id=bidone_id).first()

                if bidone:
                    prev_is_full = (
                        bool(bidone.is_full) if bidone.is_full is not None else False
                    )
                    bidone.weight = payload["weight"]
                    bidone.distance = payload["distance"]
                    bidone.is_full = payload["is_full"]
                    bidone.latitude = payload["latitude"]
                    bidone.longitude = payload["longitude"]
                    bidone.tipo = payload["tipo"]
                    bidone.fulness = payload["percentage"]
                    # bidone.citta = payload['citta']
                else:
                    prev_is_full = False
                    bidone = Bidone(
                        id=bidone_id,
                        weight=payload["weight"],
                        distance=payload["distance"],
                        is_full=payload["is_full"],
                        latitude=payload["latitude"],
                        longitude=payload["longitude"],
                        tipo=payload["tipo"],
                        fulness=payload["percentage"],
                        citta=payload["citta"],
                    )
                    db.session.add(bidone)

                db.session.commit()
                print(f"Bidone {bidone.id} aggiornato")

                # CALCOLO SE È PIENO: FASE DI TEST
                # In questa fase consideriamo pieno se:
                # - Arduino ha messo is_full = True (peso >= 0.3 kg),
                # - OPPURE il peso supera la soglia del backend,
                # - OPPURE la percentuale (percentage) >= 90.
                try:
                    w = float(payload.get("weight", 0))
                except Exception:
                    w = None

                try:
                    d = float(payload.get("distance", 0))
                except Exception:
                    d = None

                try:
                    perc = (
                        float(payload.get("percentage"))
                        if payload.get("percentage") is not None
                        else None
                    )
                except Exception:
                    perc = None

                weight_over = w is not None and w >= weight_threshold
                distance_over = d is not None and d <= distance_threshold
                payload_is_full = (
                    bool(payload.get("is_full")) if "is_full" in payload else False
                )
                is_considered_full = (
                    payload_is_full
                    or (weight_over and distance_over)
                    or (perc is not None and perc >= 90)
                )

                # Se il bidone è pieno, manda messaggio LCD con il bidone vuoto più vicino
                if is_considered_full:
                    # Opzione: inviare solo quando c'è transizione da vuoto->pieno per evitare spam
                    send_on_transition_only = True
                    if send_on_transition_only and prev_is_full:
                        print(
                            f"Bidone {bidone_id} era già segnato pieno, non invio nuovo messaggio LCD (prev_is_full={prev_is_full})"
                        )
                    else:
                        # trova bidone vuoto più vicino
                        nearest, dist_metric = find_nearest_empty_bin(app, bidone)
                        if nearest:
                            if (
                                hasattr(nearest, "latitude")
                                and nearest.latitude is not None
                                and bidone.latitude is not None
                            ):
                                message = f"Bidone {nearest.id} vuoto tra {dist_metric:.2f} km"
                            else:
                                # fallback: non abbiamo coordinate; mostriamo ID e fulness
                                try:
                                    nf = (
                                        float(nearest.fulness)
                                        if nearest.fulness is not None
                                        else None
                                    )
                                    message = f"Bidone {nearest.id} vuoto al {nf:.0f}%"
                                except Exception:
                                    message = (
                                        f"Bidone {nearest.id} vuoto"
                                    )
                        else:
                            message = "Nessun bidone vuoto nelle vicinanze"
                        
                        publish_lcd_message(client, citta, bidone_id, message)

                # Se una sola soglia è superata -> anomalia primaria
                # FASE DI TEST: disabilitiamo l'anomalia 'Discrepanza soglia' basata sulla distanza
                ENABLE_DISTANCE_BASED_ANOMALY = True
                if ENABLE_DISTANCE_BASED_ANOMALY and (
                    (weight_over and not distance_over) or (distance_over and not weight_over)
                ):
                    reason = "Discrepanza soglia"
                    details = {
                        "weight": w,
                        "distance": d,
                        "weight_threshold": weight_threshold,
                        "distance_threshold": distance_threshold,
                        "is_full": payload["is_full"],
                        "percentage": payload["percentage"],
                    }
                    publish_anomalies(client, citta, bidone_id, reason, details)
                else:
                    # in fase di test non segnaliamo questo tipo di anomalia
                    pass

                # Controlli aggiuntivi (sanity checks)
                extra = detect_additional_anomalies(payload, bidone)
                for (atype, det) in extra:
                    publish_anomalies(client, citta, bidone_id, atype, det)

        except Exception as e:
            print(f"Errore nel processing del messaggio: {e}")


    client = mqtt.Client(client_id="server-listener")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
