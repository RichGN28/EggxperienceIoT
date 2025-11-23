import cv2
import numpy as np
from tensorflow.keras.models import load_model

# ==============================
# CONFIGURACIÓN
# ==============================
MODEL_PATH = "egg_classifier.h5"  # Nombre del modelo entrenado
IMG_SIZE = (224, 224)             # Tamaño de entrada del modelo
CLASS_NAMES = ["Damaged", "Not Damaged"]  # Orden según entrenamiento

# Cargar el modelo
print("🔹 Cargando modelo...")
model = load_model(MODEL_PATH)
print("✅ Modelo cargado correctamente.")

# Abrir cámara (0 = cámara por defecto)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ No se pudo acceder a la cámara.")
    exit()

print("🎥 Presiona 'q' para salir.")

# ==============================
# BUCLE PRINCIPAL
# ==============================
while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Error al leer el frame.")
        break

    # Preprocesamiento de imagen
    img = cv2.resize(frame, IMG_SIZE)
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    # Predicción
    prediction = model.predict(img, verbose=0)[0][0]
    label = CLASS_NAMES[1] if prediction > 0.5 else CLASS_NAMES[0]
    confidence = prediction if prediction > 0.5 else 1 - prediction

    # Mostrar resultado en pantalla
    text = f"{label} ({confidence*100:.1f}%)"
    color = (0, 255, 0) if label == "Not Damaged" else (0, 0, 255)

    cv2.putText(frame, text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.imshow("Egg Classifier", frame)

    # Salir presionando 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ==============================
# LIMPIEZA
# ==============================
cap.release()
cv2.destroyAllWindows()
print("👋 Programa terminado.")
