#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>
#include <ArduinoJson.h>
#include "lab_config.h"

String mode = "off", eventId;
uint32_t started = 0, deadline = 0, lastPoll = 0, lastSeen = 0;

void lights(bool green, bool red) {
  digitalWrite(GREEN_PIN, green ? HIGH : LOW);
  digitalWrite(RED_PIN, red ? HIGH : LOW);
}

void setup() {
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(RED_PIN, OUTPUT);
  lights(false, false);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  uint32_t now = millis();
  // Complete exactly ten flashes without blocking TLS requests disturbing the cadence.
  bool redAnimation = mode == "red_blink" && now - started < 10000;
  if (!redAnimation && now - lastPoll >= 500 && WiFi.status() == WL_CONNECTED) {
    lastPoll = now;
    BearSSL::WiFiClientSecure client;
    client.setFingerprint(TLS_FINGERPRINT);
    client.setTimeout(500);
    HTTPClient http;
    http.setTimeout(500);
    if (http.begin(client, STATUS_URL)) {
      http.addHeader("Authorization", String("Bearer ") + DEVICE_KEY);
      if (http.GET() == 200) {
        JsonDocument doc;
        if (!deserializeJson(doc, http.getString())) {
          String next = doc["event"].as<String>();
          if (next != eventId) {
            eventId = next;
            mode = doc["mode"].as<String>();
            started = millis();
          }
          deadline = millis() + min(doc["remaining_ms"].as<uint32_t>(), uint32_t(90000));
          lastSeen = millis();
        }
      }
      http.end();
    }
  }
  now = millis();
  if (WiFi.status() != WL_CONNECTED || (!redAnimation && (now - lastSeen > 3000 ||
      int32_t(now - deadline) >= 0))) {
    lights(false, false);
  } else {
    bool blink = ((now - started) / 500) % 2 == 0;
    bool redBlink = mode == "red_blink" && now - started < 10000 && blink;
    lights(mode == "green" || (mode == "green_blink" && blink), mode == "red" || redBlink);
  }
  delay(5);
}
