# LAB LOGIN LOGOUT MONITORING SYSTEM

## Overview
The **Lab Login Logout Monitoring System** (formerly NX-PRINT v2.0) is a comprehensive biometric attendance tracking solution designed for laboratory environments. It integrates an **AS608 fingerprint sensor** with a **Flask-based web dashboard** to provide secure, real-time management of student attendance. The system features a robust admin panel for managing students, timetables, and viewing detailed analytics.

## Features
- **Biometric Authentication**: Fast and secure login/logout using fingerprint scanning.
- **Timetable Integration**: Automatically validates student access based on the current semester timetable.
- **Real-time Dashboard**: Live monitoring of students currently present in the lab.
- **Admin Panel**:
  - **Student Management**: Add, modify, delete students, and register fingerprints directly from the UI.
  - **Timetable Management**: flexible scheduling with semester-wise filtering.
  - **Analytics**: Visual graphs for daily attendance trends and semester-wise distribution.
  - **Data Controls**: "Reset All Data" functionality for system refreshes.
- **Reporting**: Export detailed attendance logs to Excel/CSV.
- **Hardware feedback**: LCD display messaging and real-time status updates.

## Tech Stack
- **Backend**: Python (Flask), SQLAlchemy (SQLite)
- **Frontend**: HTML5, CSS3, JavaScript (Bootstrap, Chart.js)
- **Hardware**: 
  - Arduino / ESP32 microcontroller
  - AS608 Optical Fingerprint Sensor
  - I2C LCD Display
- **Communication**: PySerial (connects Hardware <-> Python Backend)

## Project Structure
```
├── app.py                 # Main Flask application entry point
├── database.py            # Database models and configuration
├── serial_bridge.py       # Script to bridge Arduino serial data to Flask API
├── create_admin.py        # Utility to initialize DB and create default admin
├── requirements.txt       # Python dependencies
├── arduino/               # Arduino firmware sketches
│   └── fingerprint_scanner/
├── static/                # Static assets (CSS, JS, Images)
└── templates/             # HTML Templates
```

## Setup & Installation

### 1. Hardware Setup
1.  Connect the **AS608 Fingerprint Sensor** and **LCD Display** to your Arduino board.
2.  Open the Arduino IDE and upload the sketch found in `arduino/fingerprint_scanner/`.
3.  Note the **COM Port** your Arduino is connected to (e.g., `COM3`, `COM8`, `/dev/ttyUSB0`).

### 2. Software Prerequisites
- Python 3.8 or higher
- Git

### 3. Installation Steps
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/lab-monitoring-system.git
    cd lab-monitoring-system
    ```

2.  **Create and activate a virtual environment** (recommended):
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Serial Port**:
    Open `serial_bridge.py` and find the configuration section. Update `SERIAL_PORT` to match your Arduino's port:
    ```python
    # serial_bridge.py
    SERIAL_PORT = 'COM8'  # Change this to your port
    ```

5.  **Initialize Database & Admin**:
    Run the setup script to create the database and default admin user:
    ```bash
    python create_admin.py
    ```
    This creates a default admin account:
    - **Username**: `admin`
    - **Password**: `admin123`

## Usage

### 1. Start the System
You need to run both the web server and the serial bridge.

**Terminal 1 (Web Server):**
```bash
python app.py
```
*The server will start at `http://127.0.0.1:5000`.*

**Terminal 2 (Serial Bridge):**
```bash
python serial_bridge.py
```
*This script will listen to the Arduino and forward fingerprint scans to the web server.*

### 2. Access the Dashboard
1.  Open your web browser and go to `http://127.0.0.1:5000`.
2.  Log in with the admin credentials created in the setup step.
3.  **Register Students**: Go to the "Student Management" section to add students and enroll their fingerprints.
4.  **Set Timetable**: Configure the class schedule in the "Timetable" section.
5.  **Monitor**: View live attendance on the main dashboard.

## API Endpoints
The system exposes several internal APIs used by the serial bridge:
- `POST /api/scan`: Process a fingerprint scan ID.
- `GET /api/get_command`: Check for pending commands (e.g., Register, Delete) from the server.
- `POST /api/registration_result`: Report result of a fingerprint enrollment.
- `POST /api/lcd_status`: Log LCD messages.
- `POST /api/heartbeat`: Keep-alive signal for device status.

## License
MIT License.
