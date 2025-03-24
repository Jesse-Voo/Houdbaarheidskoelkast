from flask import Flask, render_template, request, redirect, url_for, jsonify
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# File paths
BARCODE_FILE_PATH = "/home/pi/barcode/barcodes.txt"
HISTORY_FILE_PATH = "/home/pi/barcode/history.txt"


# Utility function to read data from barcodes.txt, move expired items to history, and notify about expiring items
def get_data_and_alerts():
    data = []
    alerts = []
    today = datetime.today()
    expiration_warning_date = today + timedelta(days=3)

    updated_barcodes = []
    expired_barcodes = []

    try:
        with open(BARCODE_FILE_PATH, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    barcode = parts[0]
                    name = parts[1] if len(parts) > 1 else f"AutoName-{barcode}"
                    date = parts[2] if len(parts) > 2 else ''

                    if date:
                        expire_date = datetime.strptime(date, '%Y-%m-%d')
                        if expire_date < today:  # Already expired
                            expired_barcodes.append(f"{barcode}|{name}|{date}")
                            continue  # Skip adding it to active data
                        elif today <= expire_date <= expiration_warning_date:  # Expiring soon
                            alerts.append(f"{name} (barcode: {barcode}) verloopt binnenkort op {date}.")

                    # Add non-expired items to the barcode list
                    updated_barcodes.append(f"{barcode}|{name}|{date}")
                    data.append({'barcode': barcode, 'name': name, 'date': date})
    except FileNotFoundError:
        print(f"{BARCODE_FILE_PATH} not found.")

    # Update the barcode file without expired items
    with open(BARCODE_FILE_PATH, 'w') as file:
        file.write("\n".join(updated_barcodes) + "\n")

    # Add expired items to history
    if expired_barcodes:
        with open(HISTORY_FILE_PATH, 'a') as file:
            for expired_item in expired_barcodes:
                file.write(f"{expired_item} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    return data, alerts


# Function to retrieve a name by barcode from active or expired records
def find_name_by_barcode(barcode):
    # Check active barcodes
    try:
        with open(BARCODE_FILE_PATH, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if parts[0] == barcode:
                        return parts[1] if len(parts) > 1 else f"AutoName-{barcode}"
    except FileNotFoundError:
        print(f"{BARCODE_FILE_PATH} not found.")

    # Check history for previous names
    try:
        with open(HISTORY_FILE_PATH, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if parts[0] == barcode:
                        return parts[1] if len(parts) > 1 else f"AutoName-{barcode}"
    except FileNotFoundError:
        print(f"{HISTORY_FILE_PATH} not found.")

    return None  # No matching name found


@app.route('/')
def index():
    """Render the main page to view and update barcodes."""
    data, alerts = get_data_and_alerts()
    return render_template('index.html', data=data, alerts=alerts)


@app.route('/update', methods=['POST'])
def update():
    """Update the barcodes.txt file."""
    barcodes = request.form.getlist('barcode')
    names = request.form.getlist('name')
    dates = request.form.getlist('date')

    try:
        updated_data = []
        for barcode, name, date in zip(barcodes, names, dates):
            if barcode.strip():
                name = name.strip() if name.strip() else f"AutoName-{barcode.strip()}"
                updated_data.append(f"{barcode.strip()}|{name}|{date.strip()}")

        with open(BARCODE_FILE_PATH, 'w') as file:
            file.write("\n".join(updated_data) + "\n")
    except Exception as e:
        print(f"Error updating file: {e}")

    return redirect(url_for('index'))


@app.route('/history')
def history():
    """Show the barcode scanning history."""
    try:
        with open(HISTORY_FILE_PATH, 'r') as file:
            history_lines = file.readlines()
    except FileNotFoundError:
        history_lines = []

    return render_template('history.html', history=history_lines)


@app.route('/scanner')
def scanner():
    """Render the barcode scanner page."""
    return render_template('scanner.html')


@app.route('/scan_barcode', methods=['POST'])
def scan_barcode():
    """Handle barcode data received from the camera and append it to the file."""
    data = request.json
    barcode = data.get("barcode", "").strip()

    if barcode:
        try:
            # Look up the name for this barcode
            existing_name = find_name_by_barcode(barcode)
            name = existing_name if existing_name else f"..."

            # Append the barcode to the file
            with open(BARCODE_FILE_PATH, "a") as file:
                file.write(f"{barcode}|{name}|\n")  # Add empty date as placeholder

            # Also save to history
            with open(HISTORY_FILE_PATH, "a") as file:
                file.write(f"{barcode}|{name}| - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

            return jsonify({"message": f"Barcode succesvol opgeslagen met naam '{name}'", "success": True}), 200
        except Exception as e:
            return jsonify({"message": f"Error saving barcode: {str(e)}", "success": False}), 500
    else:
        return jsonify({"message": "Invalid barcode data received", "success": False}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
