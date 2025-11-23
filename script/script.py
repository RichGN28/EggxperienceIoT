import cv2 
import numpy as np
from tensorflow.keras.models import load_model
from ultralytics import YOLO
import time

# ==============================
# CONFIGURACIÓN MODELOS
# ==============================
STATUS_MODEL_PATH = "egg_classifier.h5"  # Modelo roto / no roto
IMG_SIZE = (224, 224)
# Debe coincidir con tu entrenamiento del modelo de estado
CLASS_NAMES = ["Damaged", "Not Damaged"]

# Modelo YOLO para fertilidad
FERTILITY_MODEL_PATH = "best.pt"  # Ajusta si tu ruta es distinta

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
print("🎥 Iniciando análisis. Presiona 'q' para salir.")

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
    # Misma lógica que tu script original:
    status_label = CLASS_NAMES[1] if pred > 0.5 else CLASS_NAMES[0]
    status_conf = pred if pred > 0.5 else 1 - pred

    # Texto en español para mostrar
    if status_label == "Damaged":
        estado_es = "ROTO"
        color_estado = (0, 0, 255)  # rojo
    else:
        estado_es = "NO ROTO"
        color_estado = (0, 255, 0)  # verde

    estado_text = f"Estado: {estado_es} ({status_conf*100:.1f}%)"

    # --------------------------
    # 2) SI NO ESTÁ ROTO → FERTILIDAD CON YOLO
    # --------------------------
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
        # (toma la detección con mayor confianza si existe)
        if results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            # Índice de la box con mayor probabilidad
            best_idx = int(np.argmax(boxes.conf.cpu().numpy()))
            best_box = boxes[best_idx]
            class_id = int(best_box.cls[0].cpu().numpy())
            fert_label = fertility_model.names[class_id]  # nombre de la clase del modelo
            fert_conf = float(best_box.conf[0].cpu().numpy())

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
        cv2.imshow("EggXperience - Estado y Fertilidad", frame)

    # --------------------------
    # SALIR
    # --------------------------
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ==============================
# LIMPIEZA
# ==============================
cap.release()
cv2.destroyAllWindows()
print("👋 Programa terminado.")

