#include <Servo.h>
#include <Arduino.h>
#include <stdbool.h>
#include <math.h>
#include "HX711.h"

// HX711 circuit wiring
const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 3;

HX711 scale;

int sensor = 0;
int servoPin = 5;

int trig = 7;  
int echo = 6; 
int duration;         
float distance;

Servo servo;
const int  SERVO_CLOSE_ANGLE = 90;
const int  SERVO_OPEN_ANGLE = 20;

bool currentState = false;
float prevWeight = 0.0;   // peso precedente

//coordinate del cestino
const int floor_level = 1;
const char position[] = "sinistra";

void setup()
{
  //Serial.begin(9600);
  Serial.begin(57600);   
  pinMode(trig, OUTPUT);  
  digitalWrite(trig, LOW);   
  delayMicroseconds(2);    
  pinMode(echo, INPUT);

  servo.attach(servoPin);
  servo.write(SERVO_OPEN_ANGLE);

  //Configurazione sensore peso
  //Serial.println("Initializing the scale");
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  
  //Serial.println("Calibrating scale...")
  scale.set_scale(25892.6 / 240);
  scale.tare();

  //Serial.println("Readings:");
}

void loop()
{
  //Misura della distanza
  digitalWrite(trig, HIGH);       
  delayMicroseconds(10); 
  digitalWrite(trig, LOW);
  duration = pulseIn(echo, HIGH);
  distance = (duration / 2) * 0.0343;
  //distance = abs(distance);  
      
  //Misura del peso
  float weight = scale.get_units() / 1000.0;

  bool isFull = (distance <= 10 && weight > 300);

  //Debug
  /*Serial.println("\n\nDistance (cm): ");
  Serial.println(distance);
  Serial.println("Weight (gr): ");
  Serial.println(weight);
  Serial.println("State (isFull): ");
  Serial.println(isFull);*/

  if (isFull != currentState) {
    currentState = isFull;
    servo.write(currentState ? SERVO_CLOSE_ANGLE : SERVO_OPEN_ANGLE);
  }
  if(abs(weight - prevWeight) > 5){  // 5 è un valore soglia per evitare il rumore
    
    Serial.print("{\"floor\":"); Serial.print(floor_level);
    Serial.print(", \"position\":\""); Serial.print(position);
    Serial.print("\", \"weight\":"); Serial.print(weight);
    Serial.print(", \"distance\":"); Serial.print(distance);
    Serial.print(", \"isFull\":"); Serial.print(isFull ? "true" : "false");
    Serial.println("}");
    
  }
    
  delay(1000);
}
