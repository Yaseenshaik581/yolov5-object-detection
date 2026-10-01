import serial
import time
import csv
import threading
from datetime import datetime
from flask import Flask, request, jsonify

# === Configuration ===
SERIAL_PORT = 'COM3'           # Change this to your actual COM port (e.g., 'COM4' or '/dev/ttyUSB0')
BAUD_RATE = 9600
CSV_FILE = 'data/data.csv'

# === Flask App for Emergency Stop ===
app = Flask(__name__)
serial_conn = None  # Will hold the global serial connection

# === Write sensor values to CSV ===
def write_to_csv(weight, pressure, flex1, flex2, flex3, flex4):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["weight", "pressure", "flex_01", "flex_02", "flex_03", "flex_04"])
        writer.writerow([weight, pressure, flex1, flex2, flex3, flex4])

# === Serial Reading Thread ===
def read_serial():
    global serial_conn

    serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Give Arduino time to reset

    print("[INFO] Serial connection established.")
    serial_conn.reset_input_buffer()

    while True:
        try:
            line = serial_conn.readline().decode().strip()
            if not line:
                continue

            print(f"[{datetime.now()}] RAW: {line}")

            if all(key in line for key in ['Weight:', 'Pressure:', 'Flex1:', 'Flex2:', 'Flex3:', 'Flex4:']):
                parts = line.split('|')
                data = {}

                for part in parts:
                    key, value = part.split(':')
                    data[key.strip()] = value.strip()

                write_to_csv(
                    data.get("Weight", "0"),
                    data.get("Pressure", "0"),
                    data.get("Flex1", "OFF"),
                    data.get("Flex2", "OFF"),
                    data.get("Flex3", "OFF"),
                    data.get("Flex4", "OFF")
                )

                print(f"[Logged] {data}")
            time.sleep(0.1)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(1)

# === Flask Route for Emergency Stop ===
@app.route('/emergency_stop', methods=['POST'])
def emergency_stop():
    try:
        if serial_conn and serial_conn.is_open:
            serial_conn.write(b'STOP\n')
            print("[COMMAND] Sent STOP to Arduino.")
            return jsonify({'status': 'STOP sent'}), 200
        else:
            return jsonify({'error': 'Serial connection not open'}), 500
    except Exception as e:
        print(f"[ERROR] Failed to send STOP: {e}")
        return jsonify({'error': str(e)}), 500

# === Main Entry Point ===
if __name__ == '__main__':
    # Start the serial reading in a background thread
    t = threading.Thread(target=read_serial, daemon=True)
    t.start()

    # Run Flask server (you can change port if needed)
    app.run(port=5001, debug=False)
