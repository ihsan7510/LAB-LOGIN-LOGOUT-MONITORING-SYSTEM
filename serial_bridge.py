import serial
import time
import requests
import json

# SERIAL CONFIGURATION
# IMPORTANT: Change 'COM3' to your Arduino's port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
# IMPORTANT: Change 'COM3' to your Arduino's port
SERIAL_PORT = 'COM11' 
BAUD_RATE = 115200
API_URL = "http://127.0.0.1:5000/api/scan"
CMD_URL = "http://127.0.0.1:5000/api/get_command"
REG_RESULT_URL = "http://127.0.0.1:5000/api/registration_result"
LCD_STATUS_URL = "http://127.0.0.1:5000/api/lcd_status"
HEARTBEAT_URL = "http://127.0.0.1:5000/api/heartbeat"

# Use a session for persistent connections (faster)
session = requests.Session()

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")
        print("Please check your connection and port settings.")
        return

    print("Bridge Running. Listening for fingerprints and commands...")

    last_poll_time = 0
    last_heartbeat = 0
    poll_interval = 1.0 # Poll server every 1 second

    while True:
        try:
            # 1. READ FROM ARDUINO
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if not line: continue
                print(f"Arduino: {line}")

                if line.startswith("ID:"):
                    try:
                        fingerprint_id = int(line.split(":")[1])
                        print(f"Login Detected ID: {fingerprint_id}")
                        
                        # Send to Flask API
                        payload = {'fingerprint_id': fingerprint_id}

                        try:
                            response = session.post(API_URL, json=payload)
                            if response.status_code == 200:
                                data = response.json()
                                print(f"Server: {data.get('message')}")
                                
                                # Send Name to LCD based on type
                                name = data.get('student_name', '')
                                scan_type = data.get('scan_type', 'LOGIN') # Default to LOGIN if missing
                                status = data.get('status', 'success')

                                if status == 'search_failed': # Special case if search failed
                                    ser.write(b"MSG:Not Found\n")

                                elif status == 'error':
                                    # Handle logical errors (No Class, etc)
                                    msg = data.get('message', 'Error')
                                    # Truncate to 16 chars for LCD
                                    if len(msg) > 16: msg = msg[:16]
                                    ser.write(f"MSG:{msg}\n".encode('utf-8'))
                                    
                                elif name:
                                    if scan_type == 'LOGOUT':
                                        ser.write(f"LOGOUT:{name}\n".encode('utf-8'))
                                    else:
                                        ser.write(f"LOGIN:{name}\n".encode('utf-8'))
                            else:
                                print(f"Server Error: {response.status_code}")
                                ser.write(f"MSG:ServerErr {response.status_code}\n".encode('utf-8'))
                        except requests.exceptions.RequestException as e:
                            print(f"Connection Error: {e}")

                    except ValueError:
                        print("Invalid ID format.")

                elif line.startswith("REG_SUCCESS:"):
                    try:
                        fingerprint_id = int(line.split(":")[1])
                        print(f"Registration Success! New ID: {fingerprint_id}")

                        session.post(REG_RESULT_URL, json={'status': 'success', 'fingerprint_id': fingerprint_id})
                    except:
                        pass
                
                elif line.startswith("REG_FAIL"):
                    print("Registration Failed on Device")
                elif line.startswith("REG_FAIL"):
                    print("Registration Failed on Device")
                    session.post(REG_RESULT_URL, json={'status': 'failed', 'message': 'Device failed to enroll'})

                elif line.startswith("LCD:"):
                    msg = line[4:].strip()
                    # print(f"LCD: {msg}") # Optional logging
                    try:
                        session.post(LCD_STATUS_URL, json={'message': msg})
                    except:
                        pass

            # 2. POLL SERVER FOR COMMANDS
            current_time = time.time()
            if current_time - last_poll_time > poll_interval:
                last_poll_time = current_time
                try:
                    response = session.get(CMD_URL)
                    if response.status_code == 200:
                        data = response.json()
                        cmd_type = data.get('type')
                        
                        if cmd_type == "REGISTER":
                            print("Received REGISTER command. Sending to Arduino...")
                            ser.write(b"REGISTER\n")
                            
                        elif cmd_type == "DELETE":
                            fingerprint_id = data.get('id')
                            print(f"Received DELETE command for ID {fingerprint_id}. Sending to Arduino...")
                            command_str = f"DELETE:{fingerprint_id}\n"
                            ser.write(command_str.encode('utf-8'))
                            
                        elif cmd_type == "EMPTY_DB":
                            print("Received EMPTY_DB command. Clearing sensor...")
                            ser.write(b"EMPTY_DB\n")
                            
                except requests.exceptions.RequestException:
                    pass # Server might be down
            
            # 3. SEND HEARTBEAT (Every 2 seconds)
            if current_time - last_heartbeat > 2.0:
                last_heartbeat = current_time
                try:
                    session.post(HEARTBEAT_URL)
                except:
                    pass

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

    ser.close()

if __name__ == "__main__":
    main()
