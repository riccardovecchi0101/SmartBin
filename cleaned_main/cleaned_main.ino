#include "HX711.h"
#include <Servo.h>
#include <Arduino.h>
#include <stdbool.h>
#include <math.h>
#include <LiquidCrystal.h>

// ID e tipo bidone
const int BIN_ID = 1;
const char* TIPO = "PLASTICA";
const char* CITTA = "Modena";

// Pin sensore ultrasuoni
#define TRIG_PIN 2
#define ECHO_PIN 3

// Pin HX711
#define DOUT_PIN 13
#define SCK_PIN  12

// Servo per il coperchio
#define SERVO_PIN 4
#define ANGOLO_APERTO 20
#define ANGOLO_CHIUSO 90

LiquidCrystal lcd(5, 6, 7, 8, 9, 10);

HX711 scale;
Servo servo;

float peso = 0.0;
float distanza = 0.0;
int fulness = 0;
bool is_full = false;

unsigned long lastSend = 0;
const unsigned long SEND_INTERVAL = 2000;

String msgLCD = "";
String tipoLCD = TIPO;
unsigned long lastScroll = 0;
int scrollIndex = 0;


void setup()
{
  Serial.begin(9600);
  
  // Servo e LCD
  servo.attach(SERVO_PIN);
  servo.write(ANGOLO_APERTO);
  scale.begin(DOUT_PIN, SCK_PIN);
  scale.set_scale(104.4053);
  scale.tare();

  // Setup sensori
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(TIPO);
  lcd.setCursor(0, 1);
  lcd.print("Avvio sensori...");
}


// Misura peso in kg
float leggiPeso() {
  if (scale.is_ready()) {
    float val = scale.get_units() / 1000.0;
    if (val < 0) val = 0;
    return val; 
  } else {
    return 0.0;
  }
}

// Misura distanza in cm
float leggiDistanza() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  float distance = duration * 0.034 / 2;
  if (distance < 0 || distance > 200) distance = 200;
  return distance;
}

// Aggiorna LCD con messaggio scrollabile (riga 2)
void mostraLCD(const String &testo) {
  msgLCD = testo;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(tipoLCD);
  lcd.setCursor(0, 1);
  
  if (msgLCD.length() <= 16) {
    lcd.print(msgLCD);
  } else {
    lcd.print(msgLCD.substring(0, 16));
  }
  scrollIndex = 0;
  lastScroll = millis();
}

// Scorrimento automatico se messaggio lungo
void aggiornaScroll() {
  if (msgLCD.length() <= 16) return;
  if (millis() - lastScroll < 300) return;
  
  lastScroll = millis();
  scrollIndex++;
  
  if (scrollIndex > msgLCD.length()) scrollIndex = 0;
  
  lcd.setCursor(0, 0);
  lcd.print(tipoLCD);
  lcd.setCursor(0, 1);
  String window = msgLCD.substring(scrollIndex);
  while (window.length() < 16) window += " ";
  lcd.print(window.substring(0, 16));
}

// Invia dati su seriale
void inviaDati() {
  Serial.print("id:"); Serial.print(BIN_ID); Serial.print(",");
  Serial.print("weight:"); Serial.print(peso, 2); Serial.print(",");
  Serial.print("distance:"); Serial.print(distanza, 2); Serial.print(",");
  Serial.print("fulness:"); Serial.print(fulness); Serial.print(",");
  Serial.print("latitude:44.647000,");
  Serial.print("longitude:10.925000,");
  Serial.print("tipo:"); Serial.print(TIPO); Serial.print(",");
  Serial.print("citta:"); Serial.print(CITTA); Serial.print(",");
  Serial.print("is_full:"); Serial.print(is_full ? "1" : "0");
  Serial.println();
}

// Gestisce comando ricevuto dal gateway
void gestisciComando(const String &json) {
  if (json.indexOf("\"op\":\"CLOSE\"") >= 0) {
    servo.write(ANGOLO_CHIUSO);
    mostraLCD("Coperchio chiuso");
  } else if (json.indexOf("\"op\":\"OPEN\"") >= 0) {
    servo.write(ANGOLO_APERTO);
    mostraLCD("Coperchio aperto");
  } else {
    // altri comandi futuri
    mostraLCD("Comando sconosciuto");
  }
}


void loop() {
  peso = leggiPeso();
  distanza = leggiDistanza();

  // Calcolo fulness e is_full (stima % riempimento)
  fulness = map((int)distanza, 100, 10, 0, 100);
  if (fulness < 0) fulness = 0;
  if (fulness > 100) fulness = 100;
  is_full = (fulness >= 90);

  // Invio dati periodico
  if (millis() - lastSend >= SEND_INTERVAL) {
    lastSend = millis();
    inviaDati();
  }

  // Scorrimento messaggi
  aggiornaScroll();

  // Ricezione da seriale (comandi LCD / CMD)
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.startsWith("LCD:")) {
      String json = line.substring(4);
      int i = json.indexOf("\"msg\":\"");
      if (i >= 0) {
        int start = i + 7;
        int end = json.indexOf("\"", start);
        if (end > start) {
          String testo = json.substring(start, end);
          mostraLCD(testo);
        }
      }
  } else if (line.startsWith("CMD:")) {
    String json = line.substring(4);
      gestisciComando(json);
  }