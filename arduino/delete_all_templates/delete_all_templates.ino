#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>
#include <LiquidCrystal_I2C.h>

SoftwareSerial fingerSerial(2, 3); // RX, TX
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

LiquidCrystal_I2C lcd(0x27, 16, 2);   // Change if needed

void setup() {
  Serial.begin(9600);
  fingerSerial.begin(57600);

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0,0);
  lcd.print("AS608 Fingerprint");
  lcd.setCursor(0,1);
  lcd.print("Delete System");

  Serial.println("AS608 Fingerprint Delete All Templates");

  if (finger.verifyPassword()) {
    Serial.println("Fingerprint sensor detected!");
    lcd.clear();
    lcd.print("Sensor Detected");
  } else {
    Serial.println("Fingerprint sensor not found :(");
    lcd.clear();
    lcd.print("Sensor ERROR");
    while (1);
  }

  delay(2000);

  lcd.clear();
  lcd.print("Deleting All...");

  deleteAll();

  lcd.clear();
  lcd.print("Delete Complete!");
  delay(2000);

  finger.getTemplateCount();

  lcd.clear();
  lcd.print("Templates Left:");
  lcd.setCursor(0,1);
  lcd.print(finger.templateCount);
}

void loop() {
  // Nothing here
}

void deleteAll() {
  for (int id = 1; id <= 200; id++) {
    lcd.setCursor(0,1);
    lcd.print("ID: ");
    lcd.print(id);
    lcd.print("      ");

    uint8_t p = finger.deleteModel(id);
    if (p == FINGERPRINT_OK) {
      Serial.print("Deleted ID ");
      Serial.println(id);
    }
    delay(30);
  }
}
