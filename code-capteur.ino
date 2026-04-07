#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

#define TRIG 11
#define ECHO 10

#define LED1 0
#define LED2 1
#define BUZZER 2

#define SERVO_PIN 6

LiquidCrystal_I2C lcd(0x3F, 16, 2);
Servo servo;

long duration;
int distance;

int getDistance() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  duration = pulseIn(ECHO, HIGH);
  distance = duration * 0.034 / 2;

  return distance;
}

void setup() {
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  servo.attach(SERVO_PIN);

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print("Radar System");
  delay(2000);
  lcd.clear();
}

void loop() {

  // balayage gauche → droite
  for (int angle = 0; angle <= 180; angle += 5) {
    servo.write(angle);
    delay(50);

    int d = getDistance();

    lcd.setCursor(0, 0);
    lcd.print("Dist: ");
    lcd.print(d);
    lcd.print(" cm   ");

    if (d < 20 && d > 0) {
      digitalWrite(LED1, HIGH);
      digitalWrite(LED2, HIGH);
      digitalWrite(BUZZER, HIGH);

      lcd.setCursor(0, 1);
      lcd.print("WARNING !!!   ");
    } else {
      digitalWrite(LED1, LOW);
      digitalWrite(LED2, LOW);
      digitalWrite(BUZZER, LOW);

      lcd.setCursor(0, 1);
      lcd.print("CLEAR         ");
    }
  }

  // balayage droite → gauche
  for (int angle = 180; angle >= 0; angle -= 5) {
    servo.write(angle);
    delay(50);

    int d = getDistance();

    lcd.setCursor(0, 0);
    lcd.print("Dist: ");
    lcd.print(d);
    lcd.print(" cm   ");

    if (d < 20 && d > 0) {
      digitalWrite(LED1, HIGH);
      digitalWrite(LED2, HIGH);
      digitalWrite(BUZZER, HIGH);

      lcd.setCursor(0, 1);
      lcd.print("WARNING !!!   ");
    } else {
      digitalWrite(LED1, LOW);
      digitalWrite(LED2, LOW);
      digitalWrite(BUZZER, LOW);

      lcd.setCursor(0, 1);
      lcd.print("CLEAR         ");
    }
  }
}
