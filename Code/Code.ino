#include <Arduino.h>
#include <Servo.h>
#include <DHT.h>

// ========= PINES =========

// ANALÓGICOS
#define FSR_PIN        A0   // Fuerza
#define SOIL_PIN       A1   // Humedad del suelo
#define LDR_PIN        A2   // Fotoresistencia

// DIGITALES
#define TRIG_PIN       7
#define ECHO_PIN       8
#define DHT_PIN        3
#define DHT_TYPE       DHT11
#define BUZZER_PIN     4
#define SERVO_PIN      9
#define LED            2   // ← LED agregado

// ========= OBJETOS =========
Servo servoMotor;
DHT dht(DHT_PIN, DHT_TYPE);

// ========= SERVO SWEEP =========
unsigned long lastSweep = 0;
const long SWEEP_INTERVAL = 20;
int angle = 0;
bool dirUp = true;

uint32_t rowCount = 0;
const uint32_t HEADER_EVERY = 50;

// ========= SIRENA =========
int sirenFreq = 400;
bool sirenDirUp = true;
const int SIREN_STEP = 50;
const int SIREN_MIN = 400;
const int SIREN_MAX = 1200;

// ========= TEMPORIZADORES =========
unsigned long lastPrint = 0;
const long PRINT_INTERVAL = 200;

// ========= VARIABLES LECTURA =========
int   g_ldrValue   = 0;
int   g_soilValue  = 0;
int   g_fsrValue   = 0;
long  g_distCM     = -1;
float g_h          = NAN;
float g_t          = NAN;

// ========= ULTRASONIDO =========
long readUltrasonicCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // timeout 30ms
  if (duration == 0) return -1;

  return (duration / 2) / 29.1; // Conversión a cm
}

// ========= LED POR DISTANCIA =========
void checkLedByDistance(long distanciaCM) {
  if (distanciaCM > 0 && distanciaCM < 30) {
    digitalWrite(LED, HIGH);   // Enciende LED
  } else {
    digitalWrite(LED, LOW);    // Apaga LED
  }
}

// ========= IMPRESIÓN =========
void printHeader() {
  Serial.println();
  Serial.println("TIME_ms | ANG° | LDR | SOIL | FSR | DIST_cm | HUM_% | TEMP_C");
  Serial.println("--------|------|-----|------|-----|---------|-------|--------");
}

void printRow(uint32_t t, int ang, int ldr, int soil, int fsr, long dist, float hum, float temp) {
  Serial.print(t);
  Serial.print(" | ");

  Serial.print(ang);
  Serial.print(" | ");

  Serial.print(ldr);
  Serial.print(" | ");

  Serial.print(soil);
  Serial.print(" | ");

  Serial.print(fsr);
  Serial.print(" | ");

  if (dist < 0) Serial.print("---");
  else Serial.print(dist);
  Serial.print(" | ");

  if (isnan(hum)) Serial.print("---");
  else Serial.print(hum, 1);
  Serial.print(" | ");

  if (isnan(temp)) Serial.print("---");
  else Serial.print(temp, 1);

  Serial.println();
}

// ========= SETUP =========
void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED, OUTPUT);      // ← LED inicialización
  digitalWrite(LED, LOW);    // LED apagado al inicio

  servoMotor.attach(SERVO_PIN);
  dht.begin();
  digitalWrite(BUZZER_PIN, LOW);

  printHeader();
}

// ========= LOOP =========
void loop() {
  unsigned long now = millis();

  // --------- SERVO SWEEP ---------
  if (now - lastSweep >= SWEEP_INTERVAL) {
    lastSweep = now;

    if (dirUp) {
      angle++;
      if (angle >= 180) { angle = 180; dirUp = false; }
    } else {
      angle--;
      if (angle <= 0) { angle = 0; dirUp = true; }
    }
    servoMotor.write(angle);
  }

  // --------- LECTURA E IMPRESIÓN ---------
  if (now - lastPrint >= PRINT_INTERVAL) {
    lastPrint = now;

    // ANALÓGICOS
    g_ldrValue  = analogRead(LDR_PIN);
    g_soilValue = analogRead(SOIL_PIN);
    g_fsrValue  = analogRead(FSR_PIN);

    // DIGITALES
    g_distCM    = readUltrasonicCM();
    g_h         = dht.readHumidity();
    g_t         = dht.readTemperature();

    // --------- LED POR DISTANCIA ---------
    checkLedByDistance(g_distCM);

    // --------- BUZZER / SIRENA ---------
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

    // --------- IMPRIMIR ---------
    printRow(now, angle, g_ldrValue, g_soilValue, g_fsrValue, g_distCM, g_h, g_t);

    rowCount++;
    if (rowCount % HEADER_EVERY == 0) printHeader();
  }
}