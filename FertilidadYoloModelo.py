from ultralytics import YOLO
import cv2

# Carga tu modelo entrenado
model = YOLO("runs/detect/train/weights/best.pt")

# Abre la cámara (0 = cámara por defecto)
cap = cv2.VideoCapture(0)

# Ajustes opcionales para mayor estabilidad en macOS
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    raise Exception("❌ No se puede acceder a la cámara")

print("✅ Cámara iniciada. Presiona 'q' para salir.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ No se pudo leer el frame, intentando nuevamente...")
        continue  # Reintenta leer el siguiente frame
    
    # Detección con YOLO (método eficiente, sin bloquear el flujo)
    results = model.predict(frame, stream=False, conf=0.6, imgsz=640, verbose=False)
    
    # Mostrar resultados en pantalla
    annotated_frame = results[0].plot()
    cv2.imshow("EggXperience - YOLOv8 Detection", annotated_frame)
    
    # Si presionas 'q', se cierra la cámara
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar la cámara al terminar
cap.release()
cv2.destroyAllWindows()
print("👋 Cámara cerrada correctamente.")
