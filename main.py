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

# 센서별 Device ID (Render Environment Variables에서 로드)
# 기존 DEVICE_ID 환경 변수가 남아 있다면 시험실1에 자동 매핑됩니다.
SENSORS = {
    "storage": {
        "name": "보관실",
        "device_id": os.getenv("DEVICE_ID_STORAGE", "").strip(),
    },
    "lab1": {
        "name": "시험실1",
        "device_id": os.getenv("DEVICE_ID_LAB1", os.getenv("DEVICE_ID", "")).strip(),
    },
    "lab2": {
        "name": "시험실2",
        "device_id": os.getenv("DEVICE_ID_LAB2", "").strip(),
    },
}

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)


def fetch_device_status(device_id: str, name: str):
    if not device_id:
        return {
            "name": name,
            "configured": False,
            "success": False,
            "temperature": None,
            "humidity": None,
            "error": "환경 변수에 Device ID가 등록되지 않았습니다.",
            "raw": None,
        }

    if not openapi.is_connect():
        openapi.connect()

    response = openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")

    # 토큰이 만료(1010)된 경우 즉시 재발급 후 재요청
    if response.get("code") == 1010:
        openapi.connect()
        response = openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")

    temp = None
    humid = None
    if response.get("success"):
        for status in response.get("result", []):
            code = status.get("code")
            val = status.get("value")
            if code in ["va_temperature", "temp_current"]:
                temp = val / 10.0
            elif code in ["va_humidity", "humidity_value"]:
                humid = val / 10.0 if val > 100 else float(val)

    return {
        "name": name,
        "configured": True,
        "success": response.get("success", False),
        "temperature": temp if temp is not None else 0.0,
        "humidity": humid if humid is not None else 0.0,
        "error": None if response.get("success") else f"{response.get('msg', '조회 실패')} (코드: {response.get('code', 'N/A')})",
        "raw": response,
    }


@app.get("/")
def serve_dashboard():
    return FileResponse("index.html")


@app.get("/api/sensors")
def get_all_sensors():
    results = {}
    any_success = False

    for key, info in SENSORS.items():
        data = fetch_device_status(info["device_id"], info["name"])
        results[key] = data
        if data["success"]:
            any_success = True

    return {
        "success": any_success,
        "sensors": results,
    }


# 기존 단일 센서 주소 하위 호환 유지 (시험실1 데이터 반환)
@app.get("/api/sensor")
def get_single_sensor():
    info = SENSORS["lab1"]
    return fetch_device_status(info["device_id"], info["name"])
