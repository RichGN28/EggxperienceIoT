import os
import re

# 🔧 Cambia esto al path de tu dataset (ejemplo: "database/train/labels")
LABELS_DIR = "valid/labels"
OUTPUT_DIR = "valid/labels_yolo"

os.makedirs(OUTPUT_DIR, exist_ok=True)

for file in os.listdir(LABELS_DIR):
    if not file.endswith(".txt"):
        continue

    with open(os.path.join(LABELS_DIR, file), "r") as f:
        content = f.read().strip()

    # Extrae todos los números (clase + coordenadas)
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", content)
    if len(nums) < 5:
        print(f"❌ Skipping {file}, not enough values")
        continue

    class_id = int(nums[0])
    coords = list(map(float, nums[1:]))

    # Separa coordenadas x, y
    xs = coords[0::2]
    ys = coords[1::2]

    # Calcula la bounding box
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    width = x_max - x_min
    height = y_max - y_min

    # Guarda nuevo archivo en formato YOLO
    output_path = os.path.join(OUTPUT_DIR, file)
    with open(output_path, "w") as out:
        out.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

    print(f"✅ Converted {file}")
