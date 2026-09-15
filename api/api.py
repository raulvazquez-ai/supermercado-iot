from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient
from typing import Optional
import json
import os
import pathlib

app = FastAPI(
    title="Supermarket IoT API",
    description="API REST para monitorización de la cadena de frío. Incluye filtros avanzados y separación REST/Tiempo Real.",
    version="2.0"
)

# Permitir CORS para que el dashboard pueda consultar la API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

VALID_API_KEY = "mi-clave-secreta-2026"
INFLUX_URL = os.environ.get("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "mi-token-secreto")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "esei")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "iot_data")

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = influx_client.query_api()

def verify_api_key(x_api_key: str):
    if not x_api_key or x_api_key != VALID_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: API key inválida o ausente")

# --- SERVIR EL DASHBOARD ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard():
    html_path = pathlib.Path(__file__).parent / "dashboard.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Falta el archivo dashboard.html en la carpeta api/</h1>"

# --- ENDPOINTS REST ---
@app.get("/devices", tags=["Estado de Dispositivos"], summary="Obtener el último estado de todos los dispositivos")
def get_devices(x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    try:
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "telemetry")
          |> last()
          |> group()
        '''
        tables = query_api.query(query, org=INFLUX_ORG)
        devices = {}
        for table in tables:
            for record in table.records:
                did = record.values.get("device_id")
                devices[did] = {
                    "device_id": did,
                    "type": record.values.get("type"),
                    "last_value": record.get_value(),
                    "last_timestamp": str(record.get_time())
                }
        return {"devices": list(devices.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno de Base de Datos: {e}")

@app.get("/devices/{device_id}/telemetry", tags=["Histórico"], summary="Obtener historial con filtros temporales")
def get_telemetry(
    device_id: str,
    start: str = Query("-1h", description="Inicio del filtro temporal (ej. -1h, -30m)"),
    stop: str = Query("now()", description="Fin del filtro temporal (ej. now())"),
    limit: int = Query(50, description="Límite máximo de registros a devolver"),
    x_api_key: Optional[str] = Header(None)
):
    verify_api_key(x_api_key)
    try:
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {start}, stop: {stop})
          |> filter(fn: (r) => r._measurement == "telemetry" and r.device_id == "{device_id}")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        tables = query_api.query(query, org=INFLUX_ORG)
        readings = [{"time": str(r.get_time()), "value": r.get_value()} for table in tables for r in table.records]
        
        if not readings:
            raise HTTPException(status_code=404, detail="No se encontraron datos históricos en ese rango")
            
        return {"device_id": device_id, "readings": readings}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando InfluxDB: {e}")
    
@app.get("/devices/{device_id}/status", tags=["Estado de Dispositivos"], summary="Estado actual detallado y métricas de ventana")
def get_device_status(device_id: str, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    try:
        # Consultamos el último dato y las métricas calculadas en InfluxDB
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -5m)
          |> filter(fn: (r) => r.device_id == "{device_id}")
          |> last()
        '''
        tables = query_api.query(query, org=INFLUX_ORG)
        if not tables:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado o sin datos recientes")
        
        result = {"device_id": device_id}
        for table in tables:
            for record in table.records:
                result[record.get_field()] = record.get_value()
                result["timestamp"] = str(record.get_time())
        
        return result
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))