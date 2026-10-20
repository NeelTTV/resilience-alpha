#pragma once
// Copy to ignored lab_config.h on the authorized workstation. Never commit secrets.
#define WIFI_SSID "RESILIENCE-G<n>"
#define WIFI_PASSWORD "REPLACE_LOCALLY"
#define STATUS_URL "https://192.168.137.1:8443/auth/device/status"
#define DEVICE_KEY "REPLACE_FROM_LOCAL_SECRET"
// SHA-1 fingerprint of the LAB TLS certificate, space-separated hexadecimal.
#define TLS_FINGERPRINT "REPLACE_WITH_CERTIFICATE_FINGERPRINT"
// Common-cathode LED: GPIO5 (D1) green, GPIO4 (D2) red, each through 330 ohms.
#define GREEN_PIN 5
#define RED_PIN 4
