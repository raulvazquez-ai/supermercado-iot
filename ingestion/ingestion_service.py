import json
import os
from collections import deque
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Configuración MQTT ---
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
SUBSCRIBE_TOPIC = "supermarket/+/+/telemetry"
ALERT_TOPIC_PREFIX = "supermarket/alerts"

# --- Configuración de Ingesta (C3: Múltiples ventanas deslizantes) ---
# Cada sensor tiene su propia ventana de tiempo y umbral de alerta
DEVICE_CONFIG = {
    "temp-fridge-01": {"window_sec": 30, "threshold": 7.0},
    "temp-fridge-02": {"window_sec": 30, "threshold": -15.0},
    "co2-checkout-01": {"window_sec": 60, "threshold": 800.0},
    "ethylene-fruit-01": {"window_sec": 60, "threshold": 0.5} 
}

# --- Conexión InfluxDB ---
INFLUX_URL = os.environ.get("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "supermercado-token-2026")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "esei")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "iot_data")

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Estado: diccionario para almacenar las ventanas independientes
windows = {}

# --- CAPA 1: Validación y Filtrado ---
def validate_and_filter(payload_str):
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        return False, "JSON inválido"
    
    required = ["device_id", "type", "timestamp", "value"]
    for field in required:
        if field not in data:
            return False, f"Campo '{field}' ausente"
    
    # Extraemos el ID para saber quién falla
    device_id = data.get("device_id", "Desconocido")
    
    # Filtro del "Modo Fallo"
    if data.get("status") == "fallo" or data["value"] == -999.0:
        return False, f"[{device_id}] Dato descartado: El sensor reporta una avería (-999.0)"
        
    return True, data

# --- CAPA 2: Lógica de Negocio (Ventanas Deslizantes) ---
def process_sliding_window(device_id, timestamp_str, value):
    config = DEVICE_CONFIG.get(device_id)
    if not config:
        return None
        
    window_size = config["window_sec"]
    
    if device_id not in windows:
        windows[device_id] = deque()
    
    window = windows[device_id]
    now = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    
    window.append((now, value))
    
    cutoff = now.timestamp() - window_size
    while window and window[0][0].timestamp() < cutoff:
        window.popleft()
    
    if len(window) == 0:
        return None
    
    mean_value = sum(v for _, v in window) / len(window)
    return round(mean_value, 2)

# --- CAPA 3: Alertas ---
def generate_alerts(client, device_id, data, window_mean):
    config = DEVICE_CONFIG.get(device_id)
    if not config or window_mean is None:
        return

    threshold = config["threshold"]
    if window_mean > threshold:
        alert = {
            "device_id": device_id,
            "type": data["type"],
            "timestamp": data["timestamp"],
            "window_mean": window_mean,
            "threshold": threshold,
            "message": f"La media de {config['window_sec']}s ({window_mean}) supera el límite ({threshold})"
        }
        alert_topic = f"{ALERT_TOPIC_PREFIX}/{device_id}"
        client.publish(alert_topic, json.dumps(alert), qos=1)
        # Añadimos el device_id al print para saber de quién es la alerta
        print(f" 🚨 [{device_id}] ALERTA: {alert['message']}")

# --- CAPA 4: Almacenamiento ---
def store_influxdb(data):
    point = (
        Point("telemetry")
        .tag("device_id", data["device_id"])
        .tag("type", data["type"])
        .field("value", float(data["value"]))
    )
    # Si viene el campo humedad en el JSON, lo añadimos como campo extra
    if "humidity" in data:
        point.field("humidity", float(data["humidity"]))
        
    point.time(data["timestamp"])
    write_api.write(bucket=INFLUX_BUCKET, record=point)

# --- Punto de Entrada MQTT ---
def on_message(client, userdata, msg):
    payload_str = msg.payload.decode("utf-8")
    
    # 1. Filtro
    valid, result = validate_and_filter(payload_str)
    if not valid:
        print(f" ❌ {result}")
        return
        
    data = result
    device_id = data["device_id"]
    
    # 2. Ventana
    window_mean = process_sliding_window(device_id, data["timestamp"], data["value"])
    if window_mean is not None:
        hum_text = f" | hum={data['humidity']}%" if "humidity" in data else ""
        print(f" 📡 [TELEMETRÍA] {device_id} | actual={data['value']}{hum_text} | media_movil={window_mean}")
        # 3. Alertas
        generate_alerts(client, device_id, data, window_mean)
    
    # 4. Persistencia
    store_influxdb(data)

def on_connect(client, userdata, flags, rc):
    print(f"Conectado al broker MQTT (rc={rc})")
    client.subscribe(SUBSCRIBE_TOPIC)
    print(f"Suscrito a la ingesta de datos en: {SUBSCRIBE_TOPIC}")

client = mqtt.Client(client_id="supermercado-ingestion")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

print("=== Servicio de Ingesta Avanzado Arrancado ===")
client.loop_forever()