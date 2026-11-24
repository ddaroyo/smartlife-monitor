import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tuya_connector import TuyaOpenAPI
from fastapi.responses import FileResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENDPOINT = "https://openapi.tuyaus.com"
ACCESS_ID = os.getenv("ACCESS_ID", "")
ACCESS_SECRET = os.getenv("ACCESS_SECRET", "")
DEVICE_ID = os.getenv("DEVICE_ID", "")

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()

@app.get("/")
def serve_dashboard():
    return FileResponse("index.html")

@app.get("/api/sensor")
def get_sensor_data():
    response = openapi.get(f"/v1.0/iot-03/devices/{DEVICE_ID}/status")
    temp = 0.0
    humid = 0.0
    if response.get("success"):
        for status in response.get("result", []):
            code = status.get("code")
            val = status.get("value")
            if code in ["va_temperature", "temp_current"]:
                temp = val / 10.0
            elif code in ["va_humidity", "humidity_value"]:
                humid = val / 10.0 if val > 100 else float(val)
    return {
        "success": response.get("success", False),
        "temperature": temp,
        "humidity": humid,
        "raw": response
    }