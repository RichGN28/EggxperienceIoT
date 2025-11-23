#include <Arduino.h>
#include <Servo.h>
#include <DHT.h>

// ===== WiFi / HTTPS =====
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>

// ===== CREDENCIALES / ENDPOINT =====
const char* ssid     = "Tec-IoT";
const char* password = "spotless.magnetic.bridge"
const char* server = "https://oracleapex.com/ords/eggxperience/register/insert";

// === PINES (según lo que conectaste ahora) ===
#define SERVO_PIN   D5      // Servo señal
#define LDR_PIN     D0      // Fotoresistencia (digital)
#define TRIG_PIN    D7      // Ultrasonico TRIG
#define ECHO_PIN    D8      // Ultrasonico ECHO
#define DHT_PIN     D2      // DHT11
#define DHT_TYPE    DHT11
#define FSR_PIN     A0      // FSR (presión) ANALÓGICO
#define SOIL_D_PIN  D6      // Humedad de suelo (salida D0 del módulo) DIGITAL
#define BUZZER_PIN  D1      // Buzzer

// ====== Sensor ID ======
#define ULTRASOUND_ID 2
#define FUERZASENSOR_ID 3
#define FOTORESISTENCIA_ID 22
#define TEMP_TIERRA_ID 1
#define SENSOR_HUMEDAD_ID 21
#define SENSOR_TEMPERATURA_ID 41


// ====== OBJETOS ======
Servo servoMotor;
DHT dht(DHT_PIN, DHT_TYPE);

// ====== SERVO SWEEP ======
unsigned long lastSweep = 0;
const long SWEEP_INTERVAL = 20; // 20ms para un movimiento suave
int angle = 0;
bool dirUp = true;

// ====== FORMATO SERIAL ======
uint32_t rowCount = 0;
const uint32_t HEADER_EVERY = 50;

// ====== LÓGICA SIRENA BUZZER ======
int sirenFreq = 400; // Frecuencia inicial
bool sirenDirUp = true; // Dirección de la frecuencia
const int SIREN_STEP = 50; // Cuánto cambia la frecuencia en cada ciclo
const int SIREN_MIN = 400;
const int SIREN_MAX = 1200;

// ====== TEMPORIZADORES ======
unsigned long lastPrint = 0;
const long PRINT_INTERVAL = 200; // Leer e imprimir cada 200ms

unsigned long lastPost = 0;
const long POST_INTERVAL = 2000; // Enviar a APEX cada 2s

// ====== LECTURAS ACTUALES (buffer p/POST) ======
int   g_ldrState   = 0;
int   g_soilState  = 0;
int   g_fsrValue   = 0;
long  g_distCM     = -1;
float g_h          = NAN;
float g_t          = NAN;

// ====== WiFi helpers ======
void wifiConnect(uint16_t max_ms = 10000) {
  Serial.print("Conectando a WiFi (");
  Serial.print(ssid);
  Serial.println(") ...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - t0) < max_ms) {
    delay(250);
    Serial.print('.');
    yield();
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("No se logró conexión (timeout). Continuo offline.");
  }
}

void wifiEnsure() {
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnect(5000);
  }
}

// ====== Send Data Register ======
void sendDataRegister(int sensor_id, float value) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi desconectado, no se puede enviar.");
    return;
  }

  HTTPClient http;
  http.begin(client, server);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  // 🧩 Datos que se enviarán a la API de APEX
  String postData = "microcontroler_id=1";
  postData += "&sensor_id=" + String(sensor_id);
  postData += "&value=" + String(value, 2);

  Serial.println("\n📡 Enviando datos a Oracle APEX...");
  Serial.println("POST → " + postData);

  int httpCode = http.POST(postData);

  if (httpCode > 0) {
    Serial.printf("✅ Código HTTP: %d\n", httpCode);
    String response = http.getString();
    Serial.println("📬 Respuesta del servidor:");
    Serial.println(response);
  } else {
    Serial.printf("⚠️ Error al enviar: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ====== Ultrasonido ======
long readUltrasonicCM() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  // Espera máximo 30ms por un pulso
  long duration = pulseIn(ECHO_PIN, HIGH, 30000); 
  if (duration == 0) return -1; // Timeout
  return (duration / 2) / 29.1;
}

// ====== Impresión Serial ======
void printHeader() {
  Serial.println();
  Serial.println("TIME_ms | ANG° | LDR | SOIL | FSR | DIST_cm | HUM_% | TEMP_C | WiFi");
  Serial.println("--------|------|-----|------|-----|---------|-------|--------|-----");
}

void printRow(uint32_t t, int ang, int ldr, int soil, int fsr, long dist, float hum, float temp) {
  char distStr[12], humStr[12], tempStr[12];
  if (dist < 0) snprintf(distStr, sizeof(distStr), "---");
  else          snprintf(distStr, sizeof(distStr), "%ld", dist);
  if (isnan(hum))  snprintf(humStr,  sizeof(humStr),  "---");
  else             snprintf(humStr,  sizeof(humStr),  "%.1f", hum);
  if (isnan(temp)) snprintf(tempStr, sizeof(tempStr), "---");
  else             snprintf(tempStr, sizeof(tempStr), "%.1f", temp);

  Serial.printf("%7lu | %4d | %3d | %4d | %3d | %7s | %5s | %6s | %s\n",
                t, ang, ldr, soil, fsr, distStr, humStr, tempStr,
                (WiFi.status() == WL_CONNECTED ? "ON" : "OFF"));
}

// ====== Envío HTTPS a Oracle APEX ======
void sendToAPEX() {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure client;
  client.setInsecure(); // Acepta cualquier certificado (simple y rápido en prototipos)

  HTTPClient http;
  if (!http.begin(client, serverName)) {
    Serial.println("HTTP begin() falló");
    return;
  }

  http.addHeader("Content-Type", "application/json");

  // Construye JSON con los últimos valores leídos
  // Puedes ajustar los nombres de campos según tu APEX REST
  String json = "{";
  json += "\"ANGLE\":" + String(angle) + ",";
  json += "\"LDR\":" + String(g_ldrState) + ",";
  json += "\"SOIL\":" + String(g_soilState) + ",";
  json += "\"FSR\":" + String(g_fsrValue) + ",";
  json += "\"DIST_CM\":" + String(g_distCM) + ",";
  json += "\"HUM\":" + (isnan(g_h) ? String("null") : String(g_h, 1)) + ",";
  json += "\"TEMP_C\":" + (isnan(g_t) ? String("null") : String(g_t, 1)) + ",";
  json += "\"TIME_MS\":" + String(millis()) + ",";
  json += "\"IP\":\"" + WiFi.localIP().toString() + "\"";
  json += "}";

  int code = http.POST(json);
  Serial.printf("[APEX] POST code: %d\n", code);
  if (code > 0) {
    String resp = http.getString();
    Serial.println(resp);
  } else {
    Serial.println("[APEX] Error en POST");
  }
  http.end();
}

// ====== SETUP ======
void setup() {
  Serial.begin(115200);

  pinMode(LDR_PIN, INPUT);
  pinMode(SOIL_D_PIN, INPUT);     // salida D0 del módulo de humedad (digital)
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  servoMotor.attach(SERVO_PIN);
  servoMotor.write(angle);
  dht.begin();

  digitalWrite(BUZZER_PIN, LOW);

  // Wi-Fi
  wifiConnect();

  delay(200);
  printHeader();
}

// ====== LOOP ======
void loop() {
  unsigned long now = millis();

  // Mantener Wi-Fi sin bloquear
  if (now % 3000 < 10) { // chequeo ligero cada ~3s
    wifiEnsure();
  }

  // --- TAREA 1: Barrido del servo (cada 20ms) ---
  if (now - lastSweep >= SWEEP_INTERVAL) {
    lastSweep = now;
    if (dirUp) { angle++; if (angle >= 180) { angle = 180; dirUp = false; } }
    else       { angle--; if (angle <=   0) { angle =   0; dirUp = true;  } }
    servoMotor.write(angle);
  }

  // --- TAREA 2: Sensores, Buzzer e Impresión (cada 200ms) ---
  if (now - lastPrint >= PRINT_INTERVAL) {
    lastPrint = now;

    // Lecturas
    g_ldrState  = digitalRead(LDR_PIN);
    g_soilState = digitalRead(SOIL_D_PIN);
    g_fsrValue  = analogRead(FSR_PIN);
    g_h         = dht.readHumidity();
    g_t         = dht.readTemperature();
    g_distCM    = readUltrasonicCM();

    sendDataRegister(FOTORESISTENCIA_ID, (float)g_ldrState);
    sendDataRegister(TEMP_TIERRA_ID,    (float)g_soilState);
    sendDataRegister(FUERZASENSOR_ID,   (float)g_fsrValue);
    sendDataRegister(ULTRASOUND_ID,     (float)g_distCM);
    sendDataRegister(SENSOR_HUMEDAD_ID,  g_t);
    sendDataRegister(SENSOR_TEMPERATURA_ID, g_h);

    // Lógica del Buzzer (sirena si objeto < 20 cm)
    if (g_distCM > 0 && g_distCM < 20) {
      if (sirenDirUp) {
        sirenFreq += SIREN_STEP;
        if (sirenFreq >= SIREN_MAX) { sirenFreq = SIREN_MAX; sirenDirUp = false; }
      } else {
        sirenFreq -= SIREN_STEP;
        if (sirenFreq <= SIREN_MIN) { sirenFreq = SIREN_MIN; sirenDirUp = true; }
      }
      tone(BUZZER_PIN, sirenFreq);
    } else {
      noTone(BUZZER_PIN);
      sirenFreq = SIREN_MIN;
      sirenDirUp = true;
    }

    // Serial
    printRow(now, angle, g_ldrState, g_soilState, g_fsrValue, g_distCM, g_h, g_t);

    // Reimprimir encabezado cada N filas
    rowCount++;
    if (rowCount % HEADER_EVERY == 0) printHeader();
  }

  // --- TAREA 3: Envío periódico a APEX (cada 2s) ---
  if (now - lastPost >= POST_INTERVAL) {
    lastPost = now;
    sendToAPEX();
  }

  // Sin delay: loop rápido y cooperativo
  yield();
}