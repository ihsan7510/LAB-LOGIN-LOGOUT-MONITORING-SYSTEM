#include <Adafruit_Fingerprint.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>

// PIN CONFIGURATION
// -----------------
// 1. FINGERPRINT SENSOR (AS608)
//    - Green Wire (TX) -> Arduino Pin 2  (Software Serial RX)
//    - White Wire (RX) -> Arduino Pin 3  (Software Serial TX)
//    * DO NOT use Pins 0 & 1 (RX/TX). They are needed for USB communication
//    with the PC.

// 2. LCD DISPLAY (I2C)
//    - SDA -> Arduino SDA Pin (or A4)
//    - SCL -> Arduino SCL Pin (or A5)
//    - VCC -> 5V
//    - GND -> GND

#if defined(__AVR__) || defined(ESP8266)
// For UNO and others without hardware serial, we use software serial...
SoftwareSerial mySerial(2, 3);
#else
// For others with hardware serial, use hardware serial!
// #define mySerial Serial1
#endif

Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);
// NOTE: If LCD does not light up, change 0x27 to 0x3F
LiquidCrystal_I2C lcd(0x27, 16, 2);

// HELPER: Update LCD and send status to PC
void updateLCD(String l1, String l2 = "") {
  lcd.clear();
  lcd.print(l1);
  if (l2.length() > 0) {
    lcd.setCursor(0, 1);
    lcd.print(l2);
  }

  // SEND TO PC FOR DASHBOARD
  Serial.print("LCD:");
  Serial.print(l1);
  if (l2.length() > 0) {
    Serial.print(" | ");
    Serial.print(l2);
  }
  Serial.println();
}

void setup() {
  // 1. Init LCD First for Debugging
  lcd.init();
  lcd.backlight();
  updateLCD("Booting...");
  delay(500);

  // 2. Init Serial
  Serial.begin(115200);
  // while (!Serial); // Removed blocking check for Uno

  updateLCD("Serial OK");
  delay(500);

  // 3. Init Fingerprint Sensor
  updateLCD("Check Sensor...");
  finger.begin(57600);
  delay(5);

  if (finger.verifyPassword()) {
    updateLCD("Sensor Found!");
    delay(1000);
  } else {
    updateLCD("Sensor Error!", "Check Pins 2/3");
    while (1) {
      delay(1);
    } // Halt here if sensor fails
  }

  updateLCD("Place Finger");
}

void loop() // run over and over again
{
  // Check for serial commands from Python
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "REGISTER") {
      handleEnrollment();
    } else if (command.startsWith("DELETE:")) {
      int id = command.substring(7).toInt();
      deleteFingerprint(id);
    } else if (command == "EMPTY_DB") {
      updateLCD("CMD: EMPTY_DB", "Processing...");
      delay(1000);
      emptyDatabase();
    } else {
      // Debug: Print unknown commands to help troubleshoot
      // Serial.print("UNKNOWN_CMD:"); Serial.println(command);
    }
  }

  getFingerprintID();
  delay(50); // don't ned to run this at full speed.
}

void deleteFingerprint(int id) {
  uint8_t p = -1;
  p = finger.deleteModel(id);

  if (p == FINGERPRINT_OK) {
    Serial.println("Deleted!");
    updateLCD("Deleted ID #", String(id));
    delay(2000); // feedback
  } else {
    Serial.print("Something wrong");
    updateLCD("Delete Failed", "ID: " + String(id));
    delay(2000);
  }

  // Clear LCD and go back to normal
  updateLCD("Place Finger");
}

// ... handleEnrollment() ...

// ... handleEnrollment() ...

void handleEnrollment() {
  int id = 0;
  // Find a free ID
  for (int i = 1; i < 128; i++) {
    // Attempt to load model at i. If it fails, slot is free?
    // Actually loadModel returns FINGERPRINT_OK if occupied.
    uint8_t p = finger.loadModel(i);
    if (p != FINGERPRINT_OK) {
      id = i;
      break;
    }
  }

  if (id == 0) {
    // Fallback if full or error finding free one, just use 1
    id = 1;
  }

  Serial.println("Enrolling ID #" + String(id));
  updateLCD("Enrolling ID #", String(id));

  int p = -1;

  // 1. Wait for finger
  // Note: updateLCD clears screen, so we need to be careful if we just want to
  // update line 2 But for now, full refresh is safer for consistent state
  updateLCD("Enrolling ID #" + String(id), "Place Finger");

  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    if (p == FINGERPRINT_NOFINGER) {
      // Keep waiting
    } else if (p == FINGERPRINT_OK) {
      // Good
    } else {
      // Error
    }
  }

  // 2. Convert 1
  p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) {
    updateLCD("Image Error");
    Serial.println("REG_FAIL");
    delay(2000);
    return;
  }

  updateLCD("Remove Finger");
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }

  updateLCD("Place Same Finger");

  // 3. Wait for finger again
  p = -1;
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
  }

  // 4. Convert 2
  p = finger.image2Tz(2);
  if (p != FINGERPRINT_OK) {
    updateLCD("Image Error");
    Serial.println("REG_FAIL");
    delay(2000);
    return;
  }

  // 5. Create Model
  p = finger.createModel();
  if (p != FINGERPRINT_OK) {
    updateLCD("Mismatch!");
    Serial.println("REG_FAIL");
    delay(2000);
    return;
  }

  // 6. Store
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    updateLCD("Success! ID:", String(id));

    // IMPORTANT: Send specific success format
    Serial.print("REG_SUCCESS:");
    Serial.println(id);

    delay(2000);
  } else {
    updateLCD("Store Error");
    Serial.println("REG_FAIL");
    delay(2000);
  }

  // Clear LCD and go back to normal
  updateLCD("Place Finger");
}

uint8_t getFingerprintID() {
  uint8_t p = finger.getImage();
  switch (p) {
  case FINGERPRINT_OK:
    // Serial.println("Image taken");
    break;
  case FINGERPRINT_NOFINGER:
    return p;
  case FINGERPRINT_PACKETRECIEVEERR:
    // Serial.println("Communication error");
    return p;
  case FINGERPRINT_IMAGEFAIL:
    // Serial.println("Imaging error");
    return p;
  default:
    // Serial.println("Unknown error");
    return p;
  }

  // OK success!

  p = finger.image2Tz();
  switch (p) {
  case FINGERPRINT_OK:
    // Serial.println("Image converted");
    break;
  case FINGERPRINT_IMAGEMESS:
    Serial.println("Image too messy");
    updateLCD("Try Again", "Place Finger");
    // Wait logic handled by delay in updateLCD? No, just sequence
    delay(1000);
    return p;
  case FINGERPRINT_PACKETRECIEVEERR:
    // Serial.println("Communication error");
    return p;
  case FINGERPRINT_FEATUREFAIL:
    // Serial.println("Could not find fingerprint features");
    return p;
  case FINGERPRINT_INVALIDIMAGE:
    // Serial.println("Could not find fingerprint features");
    return p;
  default:
    // Serial.println("Unknown error");
    return p;
  }

  // OK converted!
  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    // Found a match!
    Serial.print("ID:");
    Serial.println(finger.fingerID);

    updateLCD("ID: " + String(finger.fingerID), "Checking...");

    // Wait up to 2 seconds for Name from PC
    unsigned long start = millis();
    bool nameReceived = false;
    while (millis() - start < 2000) {
      if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd.startsWith("LOGIN:")) {
          String name = cmd.substring(6);
          updateLCD("Welcome", name);
          delay(2000);
          nameReceived = true;
          break;
        } else if (cmd.startsWith("MSG:")) {
          String msg = cmd.substring(4);
          updateLCD("Status:", msg);
          delay(2000); // Show error for 2 seconds
          nameReceived = true;
          break;
        } else if (cmd.startsWith("LOGOUT:")) {
          String name = cmd.substring(7);
          updateLCD("Goodbye", name);
          delay(2000);
          nameReceived = true;
          break;
        }
      }
      delay(10);
    }

    if (!nameReceived) {
      // If no name received (e.g. PC Disconnected), just reset
      delay(500);
    }

    updateLCD("Place Finger");

  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    // Serial.println("Communication error");
    return p;
  } else if (p == FINGERPRINT_NOTFOUND) {
    // Serial.println("Did not find a match");
    updateLCD("Not Found");
    delay(2000);
    updateLCD("Place Finger");
    return p;
  } else {
    // Serial.println("Unknown error");
    return p;
  }

  return p;
}

void emptyDatabase() {
  Serial.println("Clearing Database...");
  updateLCD("Clearing...", "Please Wait");

  uint8_t p = finger.emptyDatabase();

  if (p == FINGERPRINT_OK) {
    Serial.println("DB_CLEARED");
    updateLCD("Database Empty");
  } else {
    Serial.print("DB_CLEAR_FAIL:");
    Serial.println(p);
    updateLCD("Clear Failed", "Err: " + String(p));
  }

  delay(2000);
  updateLCD("Place Finger");
}
