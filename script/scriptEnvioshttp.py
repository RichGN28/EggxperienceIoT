import cv2 
import numpy as np
from tensorflow.keras.models import load_model
from ultralytics import YOLO
import time
import requests
import urllib.parse

# ==============================
# CONFIGURACIÓN MODELOS
# ==============================
STATUS_MODEL_PATH = "egg_classifier.h5"  # Modelo roto / no roto
IMG_SIZE = (224, 224)
CLASS_NAMES = ["Damaged", "Not Damaged"]

# Modelo YOLO para fertilidad
FERTILITY_MODEL_PATH = "best.pt"

# ==============================
# CONFIGURACIÓN APEX
# ==============================
APEX_BASE_URL = "https://oracleapex.com/ords/eggxperience/artificial_intelligence"
INTEGRITY_ENDPOINT = f"{APEX_BASE_URL}/updateIntegrity"
FERTILITY_ENDPOINT = f"{APEX_BASE_URL}/updateFertilityStatus"

HEADERS_APEX = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15)",
    "Accept": "*/*",
    "Connection": "close"
}

# ==============================
# FUNCIONES PARA ENVIAR A APEX
# ==============================

def send_integrity_status(status):
    """
    Envía el estado de integridad del huevo a APEX
    status: "BROKEN" o "NOT_BROKEN"
    """
    params = {"status": status}
    url = INTEGRITY_ENDPOINT + "?" + urllib.parse.urlencode(params)
    print(f"📡 APEX Integrity GET → {url}")
    
    try:
        r = requests.get(url, timeout=30, headers=HEADERS_APEX)
        print(f"   ✓ APEX HTTP {r.status_code}")
        return True
    except Exception as e:
        print(f"   ✗ APEX Error: {e}")
        return False


def send_fertility_status(status):
    """
    Envía el estado de fertilidad del huevo a APEX
    status: "FERTIL" o "INFERTIL"
    """
    params = {"status": status}
    url = FERTILITY_ENDPOINT + "?" + urllib.parse.urlencode(params)
    print(f"📡 APEX Fertility GET → {url}")
    
    try:
        r = requests.get(url, timeout=30, headers=HEADERS_APEX)
        print(f"   ✓ APEX HTTP {r.status_code}")
        return True
    except Exception as e:
        print(f"   ✗ APEX Error: {e}")
        return False


# ==============================
# CARGA DE MODELOS
# ==============================
print("🔹 Cargando modelo de estado del huevo (roto / no roto)...")
status_model = load_model(STATUS_MODEL_PATH)
print("✅ Modelo de estado cargado.")

print("🔹 Cargando modelo YOLO de fertilidad...")
fertility_model = YOLO(FERTILITY_MODEL_PATH)
print("✅ Modelo de fertilidad cargado.")

# ==============================
# CÁMARA
# ==============================
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No se pudo acceder a la cámara.")
    exit()

# Opcional: tamaño de la imagen de la cámara
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("📷 Coloca el huevo frente a la cámara.")
print("⌛ El análisis comenzará en 5 segundos...")
time.sleep(5)
print("🎥 Iniciando análisis.")
print("   Presiona 'c' para CAPTURAR y enviar a APEX")
print("   Presiona 'q' para SALIR")

# Variables para controlar envíos
last_integrity_sent = None
last_fertility_sent = None

# ==============================
# BUCLE PRINCIPAL
# ==============================
while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Error al leer el frame.")
        break

    # --------------------------
    # 1) CLASIFICAR ROTO / NO ROTO
    # --------------------------
    img = cv2.resize(frame, IMG_SIZE)
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    pred = status_model.predict(img, verbose=0)[0][0]
    status_label = CLASS_NAMES[1] if pred > 0.5 else CLASS_NAMES[0]
    status_conf = pred if pred > 0.5 else 1 - pred

    # Determinar estado para APEX
    if status_label == "Damaged":
        estado_es = "ROTO"
        color_estado = (0, 0, 255)  # rojo
        integrity_status = "BROKEN"
    else:
        estado_es = "NO ROTO"
        color_estado = (0, 255, 0)  # verde
        integrity_status = "NOT_BROKEN"

    estado_text = f"Estado: {estado_es} ({status_conf*100:.1f}%)"

    # --------------------------
    # 2) SI NO ESTÁ ROTO → FERTILIDAD CON YOLO
    # --------------------------
    fertility_status = None
    fert_text = ""
    
    if status_label == "Not Damaged":
        # Ejecutar YOLO en el frame completo
        results = fertility_model.predict(
            frame,
            stream=False,
            conf=0.6,
            imgsz=640,
            verbose=False
        )

        # `plot()` dibuja los cuadros y las etiquetas de clase del modelo
        annotated_frame = results[0].plot()

        # Agregar también el estado (NO ROTO) arriba a la izquierda
        cv2.putText(
            annotated_frame,
            estado_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color_estado,
            2
        )

        # Opcional: mostrar también la clase de fertilidad más confiable en texto
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            # Índice de la box con mayor probabilidad
            best_idx = int(np.argmax(boxes.conf.cpu().numpy()))
            best_box = boxes[best_idx]
            class_id = int(best_box.cls[0].cpu().numpy())
            fert_label = fertility_model.names[class_id]  # nombre de la clase del modelo
            fert_conf = float(best_box.conf[0].cpu().numpy())

            # Mapear el nombre de la clase a FERTIL/INFERTIL
            # Ajusta estos nombres según tu modelo YOLO
            if "fertil" in fert_label.lower() or "fertile" in fert_label.lower():
                fertility_status = "FERTIL"
            elif "infertil" in fert_label.lower() or "infertile" in fert_label.lower():
                fertility_status = "INFERTIL"
            else:
                # Si tu modelo usa otros nombres, ajústalos aquí
                fertility_status = fert_label.upper()

            fert_text = f"Fertilidad: {fert_label} ({fert_conf*100:.1f}%)"
            cv2.putText(
                annotated_frame,
                fert_text,
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        # Instrucciones en pantalla
        cv2.putText(
            annotated_frame,
            "Presiona 'C' para capturar y enviar",
            (10, 450),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )

        cv2.imshow("EggXperience - Estado y Fertilidad", annotated_frame)

    else:
        # Si está ROTO, solo mostramos ese estado
        cv2.putText(
            frame,
            estado_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color_estado,
            2
        )
        
        cv2.putText(
            frame,
            "Presiona 'C' para capturar y enviar",
            (10, 450),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )
        
        cv2.imshow("EggXperience - Estado y Fertilidad", frame)

    # --------------------------
    # CAPTURA Y ENVÍO
    # --------------------------
    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('c') or key == ord('C'):
        print("\n📸 CAPTURANDO Y ENVIANDO A APEX...")
        
        # Enviar integridad
        print(f"   Estado de integridad detectado: {integrity_status}")
        send_integrity_status(integrity_status)
        last_integrity_sent = integrity_status
        
        # Enviar fertilidad solo si no está roto
        if fertility_status:
            print(f"   Estado de fertilidad detectado: {fertility_status}")
            send_fertility_status(fertility_status)
            last_fertility_sent = fertility_status
        else:
            print("   ℹ️  No se detectó fertilidad (huevo roto o sin detección)")
        
        print("✅ Datos enviados. Continúa análisis...\n")
    
    elif key == ord('q'):
        break

# ==============================
# LIMPIEZA
# ==============================
cap.release()
cv2.destroyAllWindows()
print("👋 Programa terminado.")