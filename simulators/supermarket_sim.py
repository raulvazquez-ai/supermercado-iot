import paho.mqtt.client as mqtt
import json
import time
import random
import os
from datetime import datetime, timezone

# --- Configuración ---
BROKER = os.environ.get("MQTT_BROKER", "localhost")
PORT = 1883
COMMAND_TOPIC = "supermarket/comandos/simulador"

# Configuración de los 4 sensores (C1: Sobresaliente)
# Añadimos estado inicial, tendencia (drift) y el 4º sensor de Etileno
# Configuración de los 4 sensores 
SENSORS = [
    {"id": "temp-fridge-01", "type": "temperature", "zone": "carniceria", "base": 3.0, "noise": 0.3, "interval": 5, "active": True, "status": "normal", "drift": 0.0, "has_humidity": True, "base_hum": 85.0, "noise_hum": 2.0},
    {"id": "temp-fridge-02", "type": "temperature", "zone": "congelados", "base": -19.0, "noise": 0.5, "interval": 5, "active": True, "status": "normal", "drift": 0.0, "has_humidity": True, "base_hum": 60.0, "noise_hum": 1.5},
    {"id": "co2-checkout-01", "type": "co2_level", "zone": "cajas", "base": 450.0, "noise": 10.0, "interval": 5, "active": True, "status": "normal", "drift": 0.0, "has_humidity": False, "queue_active": False},
    {"id": "ethylene-fruit-01", "type": "ethylene_gas", "zone": "fruteria", "base": 0.1, "noise": 0.02, "interval": 10, "active": True, "status": "normal", "drift": 0.0, "has_humidity": False, "clearing": False}
    ]
# --- Lógica de Comandos (C2: Bidireccionalidad) ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        comando = payload.get("comando")
        target_id = payload.get("sensor")

        for s in SENSORS:
            if s["id"] == target_id or target_id == "all":
                if comando == "apagar":
                    s["active"] = False
                    print(f" 🔌 [COMANDO] Sensor {s['id']} APAGADO.")
                elif comando == "encender":
                    s["active"] = True
                    s["status"] = "normal" 
                    print(f" 🔌 [COMANDO] Sensor {s['id']} ENCENDIDO.")
                elif comando == "simular_fallo":
                    s["status"] = "fallo"
                    print(f" 💥 [COMANDO] Sensor {s['id']} forzado a FALLO catastrófico.")
                elif comando == "simular_degradacion":
                    s["status"] = "degradado"
                    print(f" 📉 [COMANDO] Sensor {s['id']} forzado a DEGRADADO.")
                elif comando == "set_interval":
                    nuevo_int = payload.get("valor", 5)
                    s["interval"] = max(1, nuevo_int)
                    print(f" ⏱️ [COMANDO] Intervalo de {s['id']} cambiado a {s['interval']}s.")
    except Exception as e:
        print(f" ⚠️ Error procesando comando: {e}")

# --- Configuración Cliente MQTT ---
client = mqtt.Client(client_id="supermercado-sim-master")
client.on_message = on_message

# LWT: Last Will and Testament
client.will_set("supermarket/status/simulador", json.dumps({"status": "offline"}), qos=1, retain=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Conectado al broker MQTT")
        client.subscribe(COMMAND_TOPIC)
        client.publish("supermarket/status/simulador", json.dumps({"status": "online"}), qos=1, retain=True)
    else:
        print(f"❌ Error de conexión (rc={rc})")

client.on_connect = on_connect

# Conexión con gestión de errores básica
try:
    client.connect(BROKER, PORT, keepalive=60)
except Exception as e:
    print(f"No se pudo conectar al broker: {e}")
    exit(1)

client.loop_start()

print(f"🚀 Simulador avanzado iniciado. Escuchando comandos en: {COMMAND_TOPIC}")

# --- Bucle Principal de Simulación ---
last_updates = {s["id"]: time.time() for s in SENSORS}

try:
    while True:
        now_ts = time.time()
        
        for s in SENSORS:
            # Solo procesar si el sensor está activo y ha pasado su intervalo
            if s["active"] and (now_ts - last_updates[s["id"]] >= s["interval"]):
                
                # 1. Simulación de Escenarios (C1: Sobresaliente)
                if s["status"] == "normal":
                    dice_roll = random.random()
                    if dice_roll < 0.01:   # 1% de probabilidad de fallo catastrófico
                        s["status"] = "fallo"
                    elif dice_roll < 0.03: # 2% extra de probabilidad de modo degradado
                        s["status"] = "degradado"
                
                # Mecánica de autorrecuperación (Los técnicos llegan)
                elif s["status"] in ["fallo", "degradado"]:
                    if random.random() < 0.10: # 10% de probabilidad de arreglo en cada ciclo
                        s["status"] = "normal"
                        s["drift"] = 0.0  # Los técnicos también calibran y quitan la deriva temporal
                
                # 2. Generación de valor según estado
                if s["status"] == "fallo":
                    value = -999.0
                else:
                    current_noise = s["noise"] * (3 if s["status"] == "degradado" else 1)
                    
                    if s["status"] == "normal":
                        
                        # --- CÁLCULO DE MEDIA MÓVIL LOCAL EN EL SIMULADOR ---
                        if "history" not in s:
                            s["history"] = []
                        
                        valor_actual_crudo = s["base"] + s["drift"]
                        s["history"].append(valor_actual_crudo)
                        
                        # Guardamos solo los últimos 6 valores para hacer la media
                        if len(s["history"]) > 6:
                            s["history"].pop(0)
                            
                        media_movil_local = sum(s["history"]) / len(s["history"])

                        # --- LÓGICA ESPECIAL: ETILENO (Frutería) ---
                        if s["type"] == "ethylene_gas":
                            if s.get("clearing", False):
                                s["drift"] -= 0.1
                                if s["drift"] <= 0:
                                    s["drift"] = 0.0
                                    s["clearing"] = False 
                            else:
                                s["drift"] += random.uniform(0.04, 0.08)
                                # Se compara con la media móvil local, no con el valor crudo
                                if media_movil_local >= 0.5:
                                    if random.random() < 0.30:
                                        s["clearing"] = True
                                        print(f" 👷 [MANTENIMIENTO] Trabajador retirando fruta en {s['id']}...")

                        # --- LÓGICA ESPECIAL: CO2 (Cajas) ---
                        elif s["type"] == "co2_level":
                            if s.get("queue_active", False):
                                s["drift"] += random.uniform(20.0, 40.0) 
                                if random.random() < 0.05: 
                                    s["queue_active"] = False
                                    s["clearing_queue"] = True 
                                    print(f" 🛒 [CAJAS] La cola en {s['id']} se ha disipado.")
                            
                            elif s.get("clearing_queue", False):
                                s["drift"] -= random.uniform(30.0, 50.0) 
                                if s["drift"] <= 0:
                                    s["drift"] = 0.0
                                    s["clearing_queue"] = False 
                            
                            else:
                                if random.random() < 0.40:
                                    s["drift"] += random.uniform(5.0, 15.0)
                                else:
                                    s["drift"] -= random.uniform(6.0, 18.0)
                                    
                                if random.random() < 0.04: 
                                    s["queue_active"] = True
                                    print(f" 🛒 [CAJAS] Aglomeración detectada en {s['id']}...")
                                    
                            s["drift"] = max(0.0, min(s["drift"], 600.0))

                        # --- LÓGICA ESPECIAL: TEMPERATURA (Cámaras) ---
                        else:
                            umbral = 7.0 if "fridge-01" in s["id"] else -15.0
                            # Se compara con la media móvil local, no con el valor crudo
                            esta_en_alerta = media_movil_local >= umbral

                            if s.get("is_degraded", False):
                                if "fridge-02" in s["id"]:
                                    s["drift"] += random.uniform(0.8, 1.5)
                                else:
                                    s["drift"] += random.uniform(0.4, 1.0)
                                    
                                prob_arreglo = 0.50 if esta_en_alerta else 0.20
                                if random.random() < prob_arreglo:
                                    s["is_degraded"] = False
                                    print(f" 🔧 [MANTENIMIENTO] Motor de {s['id']} reparado.")
                            else:
                                prob_degradar = 0.05 if esta_en_alerta else 0.10
                                if random.random() < prob_degradar:
                                    s["is_degraded"] = True
                                    print(f" ⚠️ [ALERTA INTERNA] Motor de {s['id']} degradado.")
                                else:
                                    s["drift"] += random.uniform(-0.5, 0.5)
                                    if s["drift"] > 0: s["drift"] -= 0.1
                                    
                            s["drift"] = max(0.0, min(s["drift"], 15.0))
                    
                    # El valor final se genera aplicando el ruido a la base + deriva
                    value = random.gauss(s["base"] + s["drift"], current_noise)
                    
                # 3. Construcción del Payload
                payload = {
                    "device_id": s["id"],
                    "type": s["type"],
                    "status": s["status"],
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                    "value": round(value, 2)
                }
                
                # Inyectamos la humedad si el sensor dispone de ella y no está averiado
                if s["has_humidity"] and s["status"] != "fallo":
                    hum_val = random.gauss(s["base_hum"], s["noise_hum"])
                    payload["humidity"] = round(hum_val, 2)
                
                # 4. Publicación (C2: QoS 1 y Jerarquía)
                topic = f"supermarket/{s['zone']}/{s['id']}/telemetry"
                client.publish(topic, json.dumps(payload), qos=1)
                
                hum_text = f" | hum={payload['humidity']}%" if "humidity" in payload else ""
                print(f"📡 [{s['status'].upper()}] {s['id']}: val={payload['value']}{hum_text} en {topic}")
                last_updates[s["id"]] = now_ts
        
        time.sleep(0.5) # Pequeño respiro para el procesador

except KeyboardInterrupt:
    print("\n🛑 Simulación finalizada por el usuario.")
    client.publish("supermarket/status/simulador", json.dumps({"status": "offline"}), qos=1, retain=True)
    client.loop_stop()
    client.disconnect()