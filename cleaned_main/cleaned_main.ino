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
const int SERVO_CLOSE_ANGLE = 0;
const int SERVO_OPEN_ANGLE  = 90;
const int floor_level = 1;
const int id = 1;

Servo servo;
LiquidCrystal lcd(5, 6, 7, 8, 9, 10);

// === Variabili di stato ===
float distance = 0.0;
float percentage = 0.0;
float prevWeight = 0.0;
String binType = "CARTA";
bool is_full = false;
const float WEIGHT_FULL_THRESHOLD    = 0.30; // kg - soglia per diventare pieno
const float WEIGHT_EMPTY_THRESHOLD   = 0.25; // kg - soglia per tornare vuoto
const float DISTANCE_FULL_THRESHOLD  = 10.0; // cm - sotto questo è “pieno”
const float DISTANCE_EMPTY_THRESHOLD = 12.0; // cm - sopra questo può tornare “vuoto”

typedef enum State{CLOSED, OPEN};
State current_state = OPEN;

// === Coordinate Bidone ===
double latitude = 44.6470;
double longitude = 10.9250;

// === Modalità di funzionamento ===
typedef enum Mode
{
  MODE_AUTO,
  MODE_UNLOCKED,
  MODE_LOCKED
};
Mode currentMode = MODE_AUTO;

// === Variabili LCD ===
String currentMessage = "Cestino aperto";
String backendMessage = "";
bool hasBackendMessage = false;

unsigned long fullMessageStart = 0;
const unsigned long FULL_MESSAGE_DURATION = 2000; // 2 secondi di "Cestino pieno"

int scrollIndex = 0;
unsigned long lastScrollTime = 0;
const unsigned long scrollDelay = 500; // ms
const int lineLength = 16;

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000; // 5 secondi

// === Variiabili delay per l'apertura in mode = AUTO ===
unsigned long lastAutoOpenTime = 0;
bool autoClosePending = false;
const unsigned long AUTO_CLOSE_DELAY = 4000;  // 4 secondi

// === PROTOTIPI ===
void apri_cestino();
void chiudi_cestino();
void gestisciMessaggiLCD();
void stampaHeaderLCD();

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
  lcd.clear();
  stampaHeaderLCD();
  lcd.setCursor(0,1);
  lcd.print("Cestino aperto   ");
  
  servo.detach();

}

void loop() {
  // Misura distanza
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);

  // Misura distanza
  long duration = pulseIn(echo, HIGH);
  distance = (duration / 2.0) * 0.0343;

  // Misura peso
  float weight = scale.get_units() / 1000.0;

  // dead-zone attorno allo zero (ad esempio 50 grammi)
  if (fabs(weight) < 0.05) {
    weight = 0.0;
  }

  /* Calcolo percentuale riempimento
  float fullnessFromDistance = map(distance, bin_height, 0, 0, 100); 
  fullnessFromDistance = constrain(fullnessFromDistance, 0, 100);

  float fullnessFromWeight = (weight / maxWeight) * 100.0;
  fullnessFromWeight = constrain(fullnessFromWeight, 0, 100);

  // Prendo il valore "più critico"
  float percentage = max(fullnessFromDistance, fullnessFromWeight);*/
  
  percentage = 100.0 - (distance / bin_height) * 100.0;
  if (percentage < 0) percentage = 0;
  if (percentage > 100) percentage = 100;
  
  // Stato di pieno (test value)
  is_full =  (weight >= 0.3); // >0.3kg (modifica se serve)
  // Stato di pieno
  //is_full = (distance <= 10 && weight > 0.3); // >0.3kg (modifica se serve)
  bool full_condition = (weight >= WEIGHT_FULL_THRESHOLD && distance <= DISTANCE_FULL_THRESHOLD);
  bool empty_condition = (weight <= WEIGHT_EMPTY_THRESHOLD || distance >= DISTANCE_EMPTY_THRESHOLD);

  /*if (!is_full && full_condition) {
    is_full = true;
  } else if (is_full && empty_condition) {
    is_full = false;
  }*/

  // Gestione servo in base alla modalità
  if (currentMode == MODE_AUTO) {
    // logica classica: chiudi se pieno, apri se vuoto
    if (is_full != (current_state == CLOSED)) {
      
      if (!is_full) {
        // Bidone vuoto -> apri subito
        autoClosePending = false;  // annulla eventuale chiusura programmata

        if (current_state != OPEN) {
          currentMessage = "Cestino aperto";
          apri_cestino();
        }
      } 
      else {
        // Bidone pieno -> ritardo di 4 secondi prima di chiudere
        if (current_state == OPEN) {
          // Se è ancora aperto, prepariamo/gestiamo il timer
          if (!autoClosePending) {
            // Primo istante in cui rileviamo "pieno"
            autoClosePending = true;
            lastAutoOpenTime = millis();
            currentMessage = "Attendere..";
          } else {
            // Timer già avviato -> controlliamo se sono passati 6 secondi
            if (millis() - lastAutoOpenTime >= AUTO_CLOSE_DELAY) {
              // Tempo scaduto -> chiudi cestino
              currentMessage = "Cestino pieno";
              chiudi_cestino();
              autoClosePending = false; // reset
            }
          }
        }
      }
    }
  } else if (currentMode == MODE_UNLOCKED) {
    // in modalità unlocked lo vogliamo sempre aperto
    if (current_state != OPEN) {
      currentMessage = "Apertura manuale";
      apri_cestino();
    }
  } else if (currentMode == MODE_LOCKED) {
    // in modalità locked lo vogliamo sempre chiuso
    if (current_state != CLOSED) {
      currentMessage = "Chiusura forzata";
      chiudi_cestino();
    }
  }

  //CONDIZIONE DA USARE : if (abs(weight - prevWeight) > 0.01 && millis() - lastSendTime >= sendInterval)
  // Invio dati periodico
  if (0.01 && millis() - lastSendTime >= sendInterval) {
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
  /*servo.write(SERVO_OPEN_ANGLE);
  current_state = OPEN;
  
  stampaHeaderLCD();
  currentMessage = "Cestino aperto";
  scrollIndex = 0;
  lcd.setCursor(0, 1);
  lcd.print("Cestino aperto   ");

  delay(600);
  servo.detach();*/
  if (current_state == OPEN) return;

  servo.attach(servoPin);
  servo.write(SERVO_OPEN_ANGLE);
  delay(500);
  servo.detach();

  current_state = OPEN;

  lcd.clear();
  stampaHeaderLCD();
  //currentMessage = "Cestino aperto";
  hasBackendMessage = false;
  backendMessage = "";
  scrollIndex = 0;
  lastScrollTime = 0;
}

void chiudi_cestino() {
  /*
  servo.write(SERVO_CLOSE_ANGLE);
  current_state = CLOSED;
  
  stampaHeaderLCD();
  currentMessage = "Cestino pieno";
  scrollIndex = 0;
  lcd.setCursor(0, 1);
  lcd.print("Cestino pieno    ");
  
  delay(600);
  servo.detach();
  */
  if (current_state == CLOSED) return;

  servo.attach(servoPin);
  servo.write(SERVO_CLOSE_ANGLE);
  delay(500);
  servo.detach();

  current_state = CLOSED;

  stampaHeaderLCD();
  //currentMessage = "Cestino pieno";
  fullMessageStart = millis(); // da ora in poi contiamo i 3 secondi
  scrollIndex = 0;
  lastScrollTime = 0;
}

void gestisciMessaggiLCD() {
  // 1) Lettura eventuale messaggio da seriale
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) {
      return;
    }

    // Comandi remoti
    if (line.startsWith("CMD:")) {
      String cmd = line.substring(4);
      cmd.trim();
      cmd.toUpperCase();

      if (cmd == "AUTO") {
        currentMode = MODE_AUTO;
        if (current_state == OPEN)
          currentMessage = "Cestino aperto";
        else
          currentMessage = "Cestino pieno";
      } else if (cmd == "UNLOCKED") {
        currentMode = MODE_UNLOCKED;
        currentMessage = "Apertura manuale";
        apri_cestino();
      } else if (cmd == "LOCKED") {
        currentMode = MODE_LOCKED;
        currentMessage = "Chiusura forzata";
        chiudi_cestino();
      }
      return;
    }

    scrollIndex = 0;
    lcd.clear();

    // Se il loader ha mandato un messaggio JSON tipo:
    // {"message":"Bidone più vicino vuoto: ID 3 - distanza 0.12 km"}
    if (line.startsWith("{")) {
      int msgPos = line.indexOf("\"message\"");
      if (msgPos >= 0) {
        int colonPos = line.indexOf(":", msgPos);
        int firstQuote = line.indexOf("\"", colonPos);
        int secondQuote = line.indexOf("\"", firstQuote + 1);
        if (firstQuote >= 0 && secondQuote > firstQuote) {
          backendMessage = line.substring(firstQuote + 1, secondQuote);
          hasBackendMessage = true;
          scrollIndex = 0;
          lastScrollTime = 0;
        } else {
          // fallback: se il parsing fallisce, mostro l'intera linea come backendMessage
          backendMessage = line;
          hasBackendMessage = true;
          scrollIndex = 0;
          lastScrollTime = 0;
        }
      } else {
        backendMessage = line;
        hasBackendMessage = true;
        scrollIndex = 0;
        lastScrollTime = 0;
      }
    }
    // Messaggio anomalia (testo normale)
     else if (line.startsWith("Anomalia:")) {
      currentMessage = line;
      hasBackendMessage = false;
      backendMessage = "";
      chiudi_cestino();
      scrollIndex = 0;
      lastScrollTime = 0;
    }
    // Altri messaggi normali (plain text)
     else {
      currentMessage = line;
      hasBackendMessage = false;
      backendMessage = "";
      scrollIndex = 0;
      lastScrollTime = 0;
    }
  }

  // 2) Scelta del messaggio da mostrare sulla seconda riga
  String messageToShow;

  // Se il cestino è chiuso e siamo ancora nei 3 secondi dalla chiusura
  if (current_state == CLOSED && (millis() - fullMessageStart) < FULL_MESSAGE_DURATION) {
    // Mostro "Cestino pieno"
    messageToShow = currentMessage;   // deve essere "Cestino pieno"
  }
  // Altrimenti, se ho un messaggio dal backend, mostro quello
  else if (hasBackendMessage) {
    messageToShow = backendMessage;
  }
  // Altrimenti, mostro il currentMessage (es. "Cestino aperto", "Cestino chiuso", ecc.)
  else {
    messageToShow = currentMessage;
  }

  // 3) Stampa sul display
  // Prima riga: sempre il tipo del bidone
  stampaHeaderLCD();

  if (messageToShow.length() <= lineLength) {
    // Messaggio corto: niente scroll
    lcd.setCursor(0, 1);
    String line = messageToShow;
    if (line.length() < lineLength) {
      line += String("                ").substring(0, 16 - line.length());
    }
    lcd.print(line);
  } else {
    // Messaggio lungo: scroll sulla seconda riga
    if (millis() - lastScrollTime >= scrollDelay) {
      lastScrollTime = millis();

      if (scrollIndex + lineLength > messageToShow.length()) {
        scrollIndex = 0; 
      }
      
      String toDisplay = messageToShow.substring(scrollIndex, scrollIndex + lineLength);
      lcd.setCursor(0, 1);
      lcd.print(toDisplay);
      
      scrollIndex++;
    }
  }
}

void stampaHeaderLCD() {
  lcd.setCursor(0,0);
  String header = binType;
  if (header.length() > 16) header = header.substring(0, 16);
  lcd.print(header);
  // padding con spazi per pulire la riga
  for (int i = header.length(); i < 16; i++) {
    lcd.print(" ");
  }
}
