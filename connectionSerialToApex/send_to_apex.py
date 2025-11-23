import serial
import requests
import time
import urllib.parse

# ===========================
# CONFIG
# ===========================

SERIAL_PORT = "/dev/tty.usbserial-1140"  # CAMBIA EL NOMBRE SI ES NECESARIO
BAUD_RATE = 115200

# -------- APEX --------
APEX_URL = "https://apex.oracle.com/ords/eggxperience/register/insert"
MICROCONTROLLER_ID = 1

# Sensor IDs en tu Base de Datos
ULTRASOUND_ID         = 2
FUERZASENSOR_ID       = 3
FOTORESISTENCIA_ID    = 22
TEMP_TIERRA_ID        = 1
SENSOR_HUMEDAD_ID     = 21
SENSOR_TEMPERATURA_ID = 41

HEADERS_APEX = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15)",
    "Accept": "*/*",
    "Connection": "close"
}

# -------- UBIDOTS --------
UBIDOTS_URL = "https://industrial.api.ubidots.com/api/v1.6/devices/esp8266egg"
UBIDOTS_TOKEN = "BBUS-cNAHkkCtZKK9aOVhDe20MNi2zDqfHt"

HEADERS_UBIDOTS = {
    "X-Auth-Token": UBIDOTS_TOKEN,
    "Content-Type": "application/json"
}


# ===========================
# SEND TO APEX (GET)
# ===========================

def send_to_apex(sensor_id, value):
    params = {
        "microcontroler_id": MICROCONTROLLER_ID,
        "sensor_id": sensor_id,
        "value": value
    }

    url = APEX_URL + "?" + urllib.parse.urlencode(params)
    print(f"📡 APEX GET {url}")

    try:
        r = requests.get(
            url,
            timeout=30,
            headers=HEADERS_APEX
        )
        print(f"   → APEX HTTP {r.status_code}")
    except Exception as e:
        print(f"   ❌ APEX Error: {e}")


# ===========================
# SEND TO UBIDOTS (POST JSON)
# ===========================

def send_to_ubidots(temp, hum, weight, underground_temp, light):
    payload = {
        "Temp": {"value": temp},
        "Hum": {"value": hum},
        "Weight": {"value": weight},
        "GroundTemp": {"value": underground_temp},
        "Light": {"value": light}
    }

    print(f"📡 UBIDOTS POST → {payload}")

    try:
        r = requests.post(
            UBIDOTS_URL,
            json=payload,
            headers=HEADERS_UBIDOTS,
            timeout=30
        )
        print(f"   → UBIDOTS HTTP {r.status_code}")
        # print(r.text) # opcional
    except Exception as e:
        print(f"   ❌ UBIDOTS Error: {e}")


# ===========================
# PARSE SERIAL LINE
# ===========================

def parse_line(line):
    try:
        parts = [x.strip() for x in line.split("|")]
        if len(parts) != 8:
            return None

        _, ang, ldr, soil, fsr, dist, hum, temp = parts

        return {
            "ldr":  int(ldr),
            "soil": int(soil),
            "fsr":  int(fsr),
            "dist": int(dist) if dist != "---" else -1,
            "hum":  float(hum) if hum != "---" else None,
            "temp": float(temp) if temp != "---" else None
        }
    except:
        return None


# ===========================
# MAIN PROGRAM
# ===========================

def main():
    print("🔌 Conectando a Arduino...")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)

    print("✔ Leyendo y enviando datos...\n")

    while True:
        try:
            raw = ser.readline().decode(errors="ignore").strip()

            if not raw or raw.startswith("TIME"):
                continue

            print(f"[SERIAL] {raw}")

            data = parse_line(raw)
            if not data:
                continue

            # ------------------------------
            # ENVIAR A ORACLE APEX
            # ------------------------------
            send_to_apex(FOTORESISTENCIA_ID,    data["ldr"])
            send_to_apex(TEMP_TIERRA_ID,        data["soil"])
            send_to_apex(FUERZASENSOR_ID,       data["fsr"])
            send_to_apex(ULTRASOUND_ID,         data["dist"])

            if data["hum"]  is not None:
                send_to_apex(SENSOR_HUMEDAD_ID,    data["hum"])

            if data["temp"] is not None:
                send_to_apex(SENSOR_TEMPERATURA_ID, data["temp"])


            # ------------------------------
            # ENVIAR A UBIDOTS
            # ------------------------------

            # UBIDOTS variables = sensores asignados
            temp_value = data["temp"] if data["temp"] is not None else 0
            hum_value  = data["hum"] if data["hum"] is not None else 0
            weight     = data["fsr"]
            underground_temp = data["soil"]       # interpretado como temp suelo / humedad suelo
            light      = data["ldr"]

            send_to_ubidots(temp_value, hum_value, weight, underground_temp, light)

            time.sleep(0.2)

        except KeyboardInterrupt:
            print("\n⛔ Finalizando...")
            break


if __name__ == "__main__":
    main()
