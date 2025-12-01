#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <Servo.h>
#include <ArduinoJson.h>

// Configuración WiFi
const char* ssid = "Tec-IoT";
const char* password = "spotless.magnetic.bridge";

// Servidor
const char* server = "oracleapex.com";

// Cliente WiFi seguro
WiFiClientSecure client;

// Servos
Servo servo1;
Servo servo2;
Servo servo3;

// Pines (NodeMCU ESP8266)
const int SERVO1_PIN = D1;   // GPIO5
const int SERVO2_PIN = D2;   // GPIO4
const int SERVO3_PIN = D5;   // GPIO14

#define BUZZER_PIN D3   // Cambia si usas otro pin

// Tiempo entre consultas (en milisegundos)
const unsigned long INTERVALO_CONSULTA = 5000; // 5 segundos
unsigned long ultimaConsulta = 0;

void beep() {
  tone(BUZZER_PIN, 1200, 120);   // beep de 120 ms
  delay(150);
}


void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Inicializar servos
  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo3.attach(SERVO3_PIN);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Posición inicial (neutral)
  servo1.write(90);
  servo2.write(90);
  servo3.write(90);
  delay(1000);
  
  Serial.println("\n\n=================================");
  Serial.println("Sistema de Clasificación de Huevos");
  Serial.println("=================================\n");
  
  // Conectar a WiFi
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(1000);
  }
  
  Serial.print("\n¡Conectado a ");
  Serial.println(ssid);
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
  Serial.println();
  
  // Configurar cliente para no verificar certificados SSL
  client.setInsecure();
}

void loop() {
  // Verificar si es tiempo de hacer una nueva consulta
  if (millis() - ultimaConsulta >= INTERVALO_CONSULTA) {
    ultimaConsulta = millis();
    
    if (WiFi.status() == WL_CONNECTED) {
      consultarEstadoHuevo();
    } else {
      Serial.println("WiFi desconectado. Reconectando...");
      WiFi.reconnect();
    }
  }
}

void consultarEstadoHuevo() {
  Serial.println("--- Consultando estado del huevo ---");
  Serial.print("Conectando al servidor: ");
  Serial.println(server);
  
  // Conectar al servidor en puerto 443 (HTTPS)
  if (!client.connect(server, 443)) {
    Serial.println("¡Error! No se pudo conectar al servidor");
    return;
  }
  
  Serial.println("Conectado al servidor!");
  
  // Hacer petición HTTP GET
  client.println("GET /ords/eggxperience/artificial_intelligence/getEggStatus HTTP/1.0");
  client.println("Host: oracleapex.com");
  client.println("Connection: close");
  client.println();
  
  // Esperar respuesta del servidor
  while (client.connected()) {
    String line = client.readStringUntil('\n');
    if (line == "\r") {
      Serial.println("Encabezados recibidos");
      break;
    }
  }
  
  // Leer la respuesta JSON con un pequeño delay para asegurar recepción completa
  delay(100);
  
  String jsonResponse = "";
  while (client.available()) {
    char c = client.read();
    jsonResponse += c;
  }
  
  client.stop();
  
  if (jsonResponse.length() > 0) {
    Serial.println("\nRespuesta recibida (raw):");
    Serial.println(jsonResponse);
    
    // Limpiar la respuesta - buscar el inicio del JSON
    int jsonStart = jsonResponse.indexOf('{');
    int jsonEnd = jsonResponse.lastIndexOf('}');
    
    if (jsonStart != -1 && jsonEnd != -1 && jsonEnd > jsonStart) {
      String cleanJson = jsonResponse.substring(jsonStart, jsonEnd + 1);
      Serial.println("\nJSON limpio:");
      Serial.println(cleanJson);
      
      // Procesar la respuesta JSON limpia
      procesarRespuesta(cleanJson);
    } else {
      Serial.println("No se encontró JSON válido en la respuesta");
    }
  } else {
    Serial.println("No se recibió respuesta del servidor");
  }
  
  Serial.println("-----------------------------------\n");
}

void procesarRespuesta(String json) {
  // Crear documento JSON con mayor capacidad
  StaticJsonDocument<2048> doc;
  
  // Limpiar espacios en blanco al inicio y final
  json.trim();
  
  DeserializationError error = deserializeJson(doc, json);
  
  if (error) {
    Serial.print("Error al parsear JSON: ");
    Serial.println(error.c_str());
    Serial.print("Código de error: ");
    Serial.println(error.code());
    Serial.println("Verifica que el JSON sea válido");
    return;
  }
  
  // Extraer los valores de los dos análisis
  String fertility = "";
  String integrity = "";
  
  JsonArray items = doc["items"];
  
  for (JsonObject item : items) {
    String redNeuronal = item["nombreredneuronal"].as<String>();
    String output = item["output"].as<String>();
    
    if (redNeuronal == "FertilityAI") {
      fertility = output;
      Serial.print("Fertilidad: ");
      Serial.println(fertility);
    } else if (redNeuronal == "IntegrityAI") {
      integrity = output;
      Serial.print("Integridad: ");
      Serial.println(integrity);
    }
  }
  
  // Clasificar y mover servos según el estado
  clasificarHuevo(integrity, fertility);
}

void clasificarHuevo(String integrity, String fertility) {
  Serial.println();
  
  if (integrity == "BROKEN") {
    // Huevo roto
    Serial.println(">>> CLASIFICACIÓN: HUEVO ROTO <<<");
    moverHuevoRoto();
  } 
  else if (integrity == "NOT_BROKEN" && fertility == "FERTIL") {
    // Huevo no roto y fértil
    Serial.println(">>> CLASIFICACIÓN: HUEVO FÉRTIL <<<");
    moverHuevoFertil();
  } 
  else if (integrity == "NOT_BROKEN" && fertility == "INFERTIL") {
    // Huevo no roto e infértil
    Serial.println(">>> CLASIFICACIÓN: HUEVO INFÉRTIL <<<");
    moverHuevoInfertil();
  }
  else {
    Serial.println(">>> Estado desconocido - Posición neutral <<<");
    posicionNeutral();
  }
  beep();
}

// ========== FUNCIONES DE MOVIMIENTO DE SERVOS ==========

void moverHuevoRoto() {
  // Configuración para huevos rotos
  // Ajusta estos ángulos según tu mecanismo
  Serial.println("→ Moviendo servos para huevo ROTO...");
  
  servo1.write(100);    // Servo 1 a 0°
  // servo2.write(50);   // Servo 2 a 30°

  
  delay(2000); // Mantener posición 2 segundos
  // posicionNeutral(); // Volver a posición neutral
}

void moverHuevoFertil() {
  // Configuración para huevos fértiles (no rotos)
  // Ajusta estos ángulos según tu mecanismo
  Serial.println("→ Moviendo servos para huevo FÉRTIL...");
  
  servo1.write(0);   // Servo 1 a 45°
  servo2.write(0);   // Servo 2 a 90°

  
  delay(2000); // Mantener posición 2 segundos
  // posicionNeutral(); // Volver a posición neutral
}

void moverHuevoInfertil() {
  // Configuración para huevos infértiles (no rotos)
  // Ajusta estos ángulos según tu mecanismo
  Serial.println("→ Moviendo servos para huevo INFÉRTIL...");
  
  servo1.write(0);   // Servo 1 a 22° (punto medio)
  servo2.write(120);   // Servo 2 a 60° (punto medio)

  
  delay(2000); // Mantener posición 2 segundos
  // posicionNeutral(); // Volver a posición neutral
}

void posicionNeutral() {
  // Volver a posición neutral
  Serial.println("→ Volviendo a posición neutral...");
  
  servo1.write(90);
  servo2.write(90);
  servo3.write(90);
  
  delay(500);
}