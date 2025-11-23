import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam

# Ruta a tu dataset
dataset_path = "dataset"  # Cambia si tu carpeta tiene otro nombre

# Parámetros
img_size = (224, 224)
batch_size = 32
epochs = 50

# Generadores de imágenes (entrenamiento y validación)
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2
)

train_gen = datagen.flow_from_directory(
    dataset_path,
    target_size=img_size,
    batch_size=batch_size,
    class_mode='binary',
    subset='training'
)

val_gen = datagen.flow_from_directory(
    dataset_path,
    target_size=img_size,
    batch_size=batch_size,
    class_mode='binary',
    subset='validation'
)

# Modelo base preentrenado
base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224,224,3))
base_model.trainable = False  # Congelamos capas base

# Añadimos capas personalizadas
model = Sequential([
    base_model,
    GlobalAveragePooling2D(),
    Dropout(0.3),
    Dense(1, activation='sigmoid')
])

# Compilamos el modelo
model.compile(
    optimizer=Adam(learning_rate=0.0001),
    loss='binary_crossentropy',
    metrics=['accuracy']
)

# Entrenamos
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=epochs
)

# Guardar modelo
model.save("egg_classifier.h5")
print("✅ Modelo guardado como egg_classifier.h5")

# Ver clases
print("Clases:", train_gen.class_indices)
