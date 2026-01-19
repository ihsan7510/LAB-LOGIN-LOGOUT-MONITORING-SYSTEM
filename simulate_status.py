import requests
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

def set_status(message):
    try:
        response = requests.post(f"{BASE_URL}/api/lcd_status", json={'message': message})
        if response.status_code == 200:
            print(f"Status Updated: '{message}'")
        else:
            print(f"Failed to update status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Flask server. Is it running?")

def main():
    print("Fingerprint Animation Simulator")
    print("-------------------------------")
    print("1. Simulate 'Not Found' (Red Error)")
    print("2. Simulate 'Welcome Student' (Green Success)")
    print("3. Simulate 'Place Finger' (Neutral)")
    print("4. Auto Cycle (Demo Mode)")
    print("q. Quit")
    
    while True:
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == '1':
            set_status("Not Found")
        elif choice == '2':
            set_status("Welcome Student")
        elif choice == '3':
            set_status("Place Finger")
        elif choice == '4':
            print("Running demo loop... Press Ctrl+C to stop.")
            try:
                while True:
                    set_status("Place Finger")
                    time.sleep(2)
                    set_status("Not Found")
                    time.sleep(2)
                    set_status("Welcome Student")
                    time.sleep(2)
            except KeyboardInterrupt:
                print("\nStopped.")
        elif choice == 'q':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
