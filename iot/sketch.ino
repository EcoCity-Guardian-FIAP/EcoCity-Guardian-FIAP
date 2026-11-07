#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Configurações de Wi-Fi para a rede virtual do Wokwi
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Endereço da API de IA (Se rodar localmente no Wokwi, use o ngrok ou IP público da máquina)
const char* serverUrl = "http://SEU_IP_LOCAL:8000/api/v1/analisar-ocorrencia";

// Pinos do Sensor HC-SR04
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_ALERTA = 2;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_ALERTA, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Conectando ao WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Conectado!");
}

void loop() {
  // Medição da distância via ultrassom (em cm)
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracao = pulseIn(ECHO_PIN, HIGH);
  float dist_cm = duracao * 0.0343 / 2;
  
  // Simula o nível de água (quanto menor a distância até o sensor no topo do bueiro, maior o nível)
  float nivel_agua_cm = 100.0 - dist_cm; 
  if (nivel_agua_cm < 0) nivel_agua_cm = 0;

  Serial.printf("Leitura IoT - Nível da Água: %.2f cm\n", nivel_agua_cm);

  // Se o nível passar de 50cm, aciona LED de alerta físico e dispara POST para a IA
  if (nivel_agua_cm > 50.0) {
    digitalWrite(LED_ALERTA, HIGH);
    enviarTelemetriaParaIA(nivel_agua_cm);
  } else {
    digitalWrite(LED_ALERTA, LOW);
  }

  delay(10000); // Envia telemetria a cada 10 segundos
}

void enviarTelemetriaParaIA(float nivel_agua) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> doc;
    doc["cidadao_id"] = "SENSOR-IOT-ESP32-01";
    doc["descricao"] = "Alerta automático: elevação crítica do nível de água detectada pelo sensor IoT no Bueiro 12.";
    doc["nivel_sensor_agua_cm"] = nivel_agua;

    String jsonBody;
    serializeJson(doc, jsonBody);

    int httpCode = http.POST(jsonBody);
    if (httpCode > 0) {
      Serial.printf("Telemetria enviada com sucesso! Código HTTP: %d\n", httpCode);
    } else {
      Serial.printf("Falha no envio HTTP: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
  }
}