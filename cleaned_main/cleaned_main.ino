#include <Servo.h>
#include <Arduino.h>
#include <stdbool.h>
#include <math.h>
#include <LiquidCrystal.h>
#include "HX711.h"

// === Pin HX711 ===
const int LOADCELL_DOUT_PIN = 12;
const int LOADCELL_SCK_PIN  = 13;

HX711 scale;

// === Pin sensori e servo ===
int trig = 2;
int echo = 3;
int servoPin = 4;

// === Costanti cestino ===
const float bin_height = 25.0; // altezza del cestino in cm (modifica secondo il tuo)
const int SERVO_CLOSE_ANGLE = 20;
const int SERVO_OPEN_ANGLE  = 90;
const int floor_level = 1;

Servo servo;
LiquidCrystal lcd(5, 6, 7, 8, 9, 10);

// === Variabili di stato ===
float distance = 0.0;
float percentage = 0.0;
float prevWeight = 0.0;
bool currentState = false;
bool is_full = false;

// Coordinate o identificativi — da completare
double latitude = 44.6470;
double longitude = 10.9250;
int id = 1;

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000;

// === Variabili LCD ===
String currentMessage = "";
int scrollIndex = 0;
unsigned long lastScrollTime = 0;
const unsigned long scrollDelay = 600;
const int lineLength = 16;

// === PROTOTIPI ===
void apri_cestino();
void chiudi_cestino();
void gestisciMessaggiLCD();

void setup() {
  Serial.begin(9600);

  // Sensore distanza
  pinMode(trig, OUTPUT);
  digitalWrite(trig, LOW);
  pinMode(echo, INPUT);

  // Servo
  servo.attach(servoPin);
  servo.write(SERVO_OPEN_ANGLE);

  // HX711
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(104);
  scale.tare();

  // LCD
  lcd.begin(16, 2);
  lcd.print("Sistema avviato");
}

void loop() {
  // Misura distanza
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH);
  distance = (duration / 2.0) * 0.0343;

  // Calcolo percentuale riempimento
  percentage = 100.0 - (distance / bin_height) * 100.0;
  if (percentage < 0) percentage = 0;
  if (percentage > 100) percentage = 100;

  // Misura peso
  float weight = scale.get_units() / 1000.0;

  // Stato di pieno
  is_full = (distance <= 10 && weight > 0.3); // >0.3kg (modifica se serve)

  // Gestione servo
  if (is_full != currentState) {
    if (is_full) chiudi_cestino();
    else apri_cestino();
  }

  // Invio dati periodico
  if (abs(weight - prevWeight) > 0.01 && millis() - lastSendTime >= sendInterval) {
    prevWeight = weight;
    lastSendTime = millis();

    String data = "id:" + String(id) + ",";
    data += "floor:" + String(floor_level) + ",";
    data += "percentage:" + String(percentage) + ",";
    data += "weight:" + String(weight, 2) + ",";
    data += "distance:" + String(distance, 2) + ",";
    data += "is_full:" + String(is_full ? "1" : "0") + ",";
    data += "latitude:" + String(latitude, 6) + ",";
    data += "longitude:" + String(longitude, 6);
    Serial.println(data);
  }

  gestisciMessaggiLCD();
}

// === FUNZIONI ===

void apri_cestino() {
  servo.write(SERVO_OPEN_ANGLE);
  currentState = false;
}

void chiudi_cestino() {
  servo.write(SERVO_CLOSE_ANGLE);
  currentState = true;
}

void gestisciMessaggiLCD() {
  if (Serial.available() > 0) {
    currentMessage = Serial.readStringUntil('\n');
    currentMessage.trim();
    scrollIndex = 0;
    lcd.clear();

    if (currentMessage.startsWith("Anomalia:")) {
      chiudi_cestino();
    } else {
      chiudi_cestino();
      currentMessage = "Cestino chiuso";
    }
  }

  if (currentMessage.length() <= 32) {
    lcd.setCursor(0, 0);
    lcd.print(currentMessage.substring(0, lineLength));
    if (currentMessage.length() > lineLength) {
      lcd.setCursor(0, 1);
      lcd.print(currentMessage.substring(lineLength));
    } else {
      lcd.setCursor(0, 1);
      lcd.print("                ");
    }
  } else {
    if (millis() - lastScrollTime >= scrollDelay) {
      lastScrollTime = millis();
      lcd.setCursor(0, 0);
      lcd.print("Anomalia:       ");
      if (scrollIndex + lineLength > currentMessage.length()) scrollIndex = 0;
      String toDisplay = currentMessage.substring(scrollIndex, scrollIndex + lineLength);
      lcd.setCursor(0, 1);
      lcd.print(toDisplay + "                ");
      scrollIndex++;
    }
  }
}
